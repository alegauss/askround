"""AR25: a research question asked everywhere, its claims merged by support and its
sources ranked primary first."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from conftest import FakePost

from askround import research
from askround.cli import main
from askround.providers import Answer, Source
from askround.round import Result, Round

NOW = datetime(2026, 11, 12, tzinfo=UTC)
QUESTION = "Which open image-to-3D models allow commercial use?"
OPENAI = "TripoSR is MIT licensed. Hunyuan3D 2.1 restricts use in the EU."
GEMINI = "TripoSR uses the MIT license, so commercial use is allowed. TRELLIS is MIT too."


def _round():
    a = Answer(
        "openai",
        "m",
        OPENAI,
        {},
        sources=[
            Source("https://someblog.example/best-3d-models"),
            Source("https://github.com/VAST-AI-Research/TripoSR/blob/main/LICENSE"),
        ],
    )
    g = Answer(
        "gemini", "m", GEMINI, {}, sources=[Source("https://huggingface.co/stabilityai/TripoSR")]
    )
    return Round(
        QUESTION, NOW, [Result("openai", "m", 1, answer=a), Result("gemini", "m", 1, answer=g)]
    )


class Reader:
    def __init__(self):
        self.prompts = []

    def ask_json(self, prompt, schema):
        self.prompts.append(prompt)
        if "statements" in schema["properties"]:
            if OPENAI in prompt:
                return {
                    "statements": [
                        {"statement": "TripoSR is MIT", "quote": "TripoSR is MIT licensed"},
                        {
                            "statement": "Hunyuan3D 2.1 restricts EU use",
                            "quote": "Hunyuan3D 2.1 restricts use in the EU",
                        },
                        {"statement": "invented", "quote": "not in the answer"},
                    ]
                }
            return {
                "statements": [
                    {"statement": "TripoSR is MIT", "quote": "TripoSR uses the MIT license"},
                    {"statement": "TRELLIS is MIT", "quote": "TRELLIS is MIT too"},
                ]
            }
        return {
            "claims": [
                {"claim": "TripoSR is MIT licensed", "ids": ["openai#1:1", "gemini#1:1"]},
                {"claim": "Hunyuan3D 2.1 restricts use in the EU", "ids": ["openai#1:2"]},
            ]
        }


def test_read_keeps_only_statements_traced_to_their_passage():
    statements = research.read(_round(), Reader())
    assert [s.id for s in statements] == ["openai#1:1", "openai#1:2", "gemini#1:1", "gemini#1:2"]
    assert all(s.statement != "invented" for s in statements)


def test_merge_groups_by_support_and_ranks_primary_sources_first():
    reader = Reader()
    merged = research.merge(QUESTION, research.read(_round(), reader), reader)
    top = merged[0]
    assert top.claim == "TripoSR is MIT licensed"
    assert top.providers == ["openai", "gemini"]
    assert top.passages == {
        "openai": "TripoSR is MIT licensed",
        "gemini": "TripoSR uses the MIT license",
    }
    # the pages naming TripoSR first, the blog that names nothing last
    assert [(s["about"], s["primary"]) for s in top.sources] == [
        (True, True),
        (True, True),
        (False, False),
    ]
    assert top.sources[-1]["url"] == "https://someblog.example/best-3d-models"
    # the statement the merge left out still counts, on its own
    assert any(m.claim == "TRELLIS is MIT" and m.providers == ["gemini"] for m in merged)


def test_primary():
    assert research.primary("https://github.com/x/y")
    assert research.primary("https://example.org/LICENSE")
    assert research.primary("https://docs.example.org/start")
    assert research.primary("https://arxiv.org/abs/2403.02151")
    assert not research.primary("https://someblog.example/best-3d-models")


def test_markdown():
    reader = Reader()
    merged = research.merge(QUESTION, research.read(_round(), reader), reader)
    text = research.markdown(QUESTION, merged, ["openai", "gemini"])
    assert text.startswith(f"# Research: {QUESTION}")
    assert "## 1. TripoSR is MIT licensed" in text
    assert "Supported by 2/2: openai, gemini" in text
    assert "- [primary] https://github.com/VAST-AI-Research/TripoSR/blob/main/LICENSE" in text


class Routed(FakePost):
    def __call__(self, url, headers, body, timeout):
        if body and "text" in body and "format" in body["text"]:
            self.calls.append((url, headers, body))
            schema = body["text"]["format"]["schema"]
            if "statements" in schema["properties"]:
                data = {
                    "statements": [{"statement": "the app exists", "quote": "OpenAI says Modelado"}]
                }
            else:
                data = {"claims": [{"claim": "Modelado exists", "ids": ["openai#1:1"]}]}
            message = {"type": "output_text", "text": json.dumps(data)}
            return {"output": [{"type": "message", "content": [message]}]}
        return super().__call__(url, headers, body, timeout)


def test_cli_research(all_keys, tmp_path, capsys):
    argv = [
        "research",
        QUESTION,
        "--provider",
        "openai",
        "--extract",
        "openai",
        "--out",
        str(tmp_path),
    ]
    assert main(argv, post=Routed()) == 0
    out = capsys.readouterr().out
    assert "## 1. Modelado exists" in out
    assert list(tmp_path.glob("*/*/research.json"))


def test_research_needs_a_reader(no_keys, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "p")
    post = FakePost()
    assert main(["research", QUESTION, "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
