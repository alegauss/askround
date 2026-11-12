"""AR8: the extraction pass ranks a product by the answer's own order of
recommendations, checked against the answer's text.

The answers of 12/11/2026 were read in a chat and never kept verbatim; the notes about
them (visibility/estrategia/modelado.md) say the 'without NVIDIA' answer put Modelado
first as "best fit" in a table, and the general answer led with Modly and did not name
Modelado. The two answers below are SYNTHETIC, written in those shapes; they are not
the recorded answers.
"""

from __future__ import annotations

import json

import pytest
from conftest import OPENAI_RAW, FakePost

from askround.cli import main
from askround.extract import (
    AnthropicExtractor,
    GeminiExtractor,
    OpenAIExtractor,
    Recommendation,
    choose,
    verify,
)
from askround.mention import Mention, find, locate
from askround.providers import Answer

WITHOUT_NVIDIA = """Good news: you can do this without an NVIDIA GPU.

| App | Runs on | Notes | Verdict |
|---|---|---|---|
| Meshroom | NVIDIA (CUDA) | photogrammetry, needs many photos | Not ideal |
| Stable Fast 3D | GPU recommended | one photo | Possible |
| Modelado | CPU / any GPU (DirectML) | TripoSR, one photo | **Best fit** |

My first choice for you is **Modelado**: it runs on the CPU. CPU only: Check build.
"""

GENERAL = """1. **Modly** - the most polished photo-to-3D app for Windows (needs NVIDIA, 8 GB).
2. **Trellis Studio** - high quality meshes.
3. **Meshroom** - free photogrammetry.
"""

# what a good extraction returns for each
WITHOUT_NVIDIA_RECS = [
    {"name": "Modelado", "quote": "My first choice for you is Modelado"},
    {"name": "Stable Fast 3D", "quote": "Stable Fast 3D | GPU recommended"},
]
GENERAL_RECS = [
    {"name": "Modly", "quote": "the most polished photo-to-3D app for Windows"},
    {"name": "Trellis Studio", "quote": "high quality meshes"},
    {"name": "Meshroom", "quote": "free photogrammetry"},
]


def _answer(text, recs):
    answer = Answer("openai", "gpt-5", text, {})
    answer.recommendations = verify(text, recs)
    return answer


def test_plain_text_alone_ranks_the_table_row_not_the_verdict():
    # the table lists Modelado third; only reading "Best fit" puts it first
    assert find(WITHOUT_NVIDIA, ["Modelado"]) == Mention(True, 3)


def test_extraction_reports_first_where_it_was_first():
    found = locate(_answer(WITHOUT_NVIDIA, WITHOUT_NVIDIA_RECS), ["Modelado"])
    assert found.position == 1
    assert found.by == "extraction"
    assert found.evidence == "My first choice for you is Modelado"


def test_extraction_reports_absent_where_it_was_absent():
    found = locate(_answer(GENERAL, GENERAL_RECS), ["Modelado"])
    assert found == Mention(False)
    assert locate(_answer(GENERAL, GENERAL_RECS), ["Modly"]).position == 1


def test_an_invented_product_never_counts():
    recs = [{"name": "Nowhere Shape Studio", "quote": "made up"}, *GENERAL_RECS]
    answer = _answer(GENERAL, recs)
    assert locate(answer, ["Nowhere Shape Studio"]) == Mention(False)
    # and it does not push the real ones down
    assert locate(answer, ["Trellis Studio"]).position == 2


def test_named_but_not_recommended_has_no_rank():
    text = GENERAL + "\nUnlike Modelado, Modly needs a big GPU."
    found = locate(_answer(text, GENERAL_RECS), ["Modelado"])
    assert found == Mention(True, None, "extraction")


def test_without_extraction_plain_text_stands():
    answer = Answer("openai", "gpt-5", GENERAL, {})
    assert locate(answer, ["Meshroom"]) == Mention(True, 3)


def test_verify_marks_quotes_not_in_the_answer():
    recs = verify(GENERAL, [{"name": "Modly", "quote": "MOST polished **photo-to-3D**"}])
    assert recs == [Recommendation("Modly", "MOST polished **photo-to-3D**", True)]
    assert not verify(GENERAL, [{"name": "Modly", "quote": "the best app ever"}])[0].verified


@pytest.mark.parametrize(
    ("cls", "path"),
    [
        (OpenAIExtractor, ("text", "format", "schema")),
        (GeminiExtractor, ("generationConfig", "responseJsonSchema")),
        (AnthropicExtractor, ("output_config", "format", "schema")),
    ],
)
def test_each_extractor_asks_for_the_schema(all_keys, cls, path):
    _, _, body = cls().request("prompt", "key")
    node = body
    for step in path:
        node = node[step]
    assert node["required"] == ["recommendations", "claims"]


def test_choose_auto_takes_the_first_configured(no_keys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert choose().name == "gemini"
    with pytest.raises(ValueError, match="no extractor"):
        choose("perplexity")


def test_choose_without_any_key_is_refused(no_keys):
    with pytest.raises(ValueError, match="needs an OpenAI, Gemini or Anthropic key"):
        choose()


class Routed(FakePost):
    """Answers the round with the canned responses and the extraction calls (those
    asking for a JSON schema) with the recommendations of the canned OpenAI answer."""

    def __call__(self, url, headers, body, timeout):
        if body and "text" in body and "format" in body["text"]:
            self.calls.append((url, headers, body))
            recs = {"recommendations": [{"name": "Modelado", "quote": "OpenAI says Modelado"}]}
            return {"output": [_message(json.dumps(recs))]}
        return super().__call__(url, headers, body, timeout)


def _message(text):
    return {"type": "message", "content": [{"type": "output_text", "text": text}]}


def test_cli_extract_ranks_and_saves_the_recommendations(all_keys, tmp_path, capsys):
    post = Routed()
    argv = ["ask", "q", "--provider", "openai", "--runs", "2", "--extract", "openai"]
    code = main([*argv, "--product", "Modelado", "--out", str(tmp_path)], post=post)
    out = capsys.readouterr().out
    assert code == 0
    assert "recommends: 1. Modelado" in out
    assert "positions: #1*, #1*" in out
    assert "* ranked by the extraction pass" in out
    data = json.loads(next(tmp_path.glob("*/*/round.json")).read_text(encoding="utf-8"))
    first = data["results"][0]
    assert first["recommendations"] == [
        {"name": "Modelado", "quote": "OpenAI says Modelado", "verified": True}
    ]
    assert first["extracted_by"] == "openai:gpt-5-mini"
    row = data["products"][0]["providers"][0]
    assert row["ranked_by"] == ["extraction", "extraction"]
    assert row["evidence"] == ["OpenAI says Modelado", "OpenAI says Modelado"]


def test_cli_extract_without_a_key_is_refused_before_the_round(no_keys, monkeypatch, tmp_path):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "p")
    post = FakePost()
    code = main(["ask", "q", "--extract", "--out", str(tmp_path)], post=post)
    assert code == 2
    assert post.calls == []  # nothing was paid for


def test_a_failed_extraction_keeps_the_plain_reading(all_keys, tmp_path, capsys):
    class Broken(FakePost):
        def __call__(self, url, headers, body, timeout):
            if body and "text" in body:
                return {"output": [_message("not json")]}
            return super().__call__(url, headers, body, timeout)

    argv = ["ask", "q", "--provider", "openai", "--runs", "1", "--extract", "openai"]
    code = main([*argv, "--product", "Modelado", "--out", str(tmp_path)], post=Broken())
    out = capsys.readouterr().out
    assert code == 0
    assert "[extraction failed] JSONDecodeError" in out
    assert "openai      1/1 runs" in out
    assert OPENAI_RAW["model"] in out
