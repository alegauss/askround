"""AR17: discovery writes variants of a seed question and ranks them by how they lead
the assistants to the product."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from conftest import FakePost

from askround.cli import main
from askround.discover import generate, rank, score
from askround.product import Fact, Product, Question
from askround.providers import Answer, Locale
from askround.round import Result, Round

NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=UTC)
EXAMPLE = Path(__file__).parent.parent / "examples" / "modelado.toml"
SEED = "free offline app photo to 3D model on Windows"
PRODUCT = Product(
    "Modelado",
    places=["alegauss.github.io/modelado"],
    facts=[Fact("Runs without an NVIDIA GPU", "Yes")],
)

VARIANTS = {
    "questions": [
        {
            "text": "photo to 3D on Windows without an NVIDIA GPU",
            "axis": "constraint",
            "locale": "",
        },
        {"text": "photo to a relief STL for 3D printing", "axis": "use case", "locale": ""},
        {"text": "app de foto para 3D só na CPU", "axis": "language", "locale": "BR:pt-BR"},
        {"text": "is Modelado good for photo to 3D?", "axis": "constraint", "locale": ""},
        {"text": "see alegauss.github.io/modelado for 3D", "axis": "use case", "locale": ""},
    ]
}


class Writer:
    name, model = "openai", "gpt-5-mini"

    def __init__(self):
        self.prompts = []

    def ask_json(self, prompt, schema):
        self.prompts.append(prompt)
        return VARIANTS


def test_generate_drops_variants_that_name_the_product():
    writer = Writer()
    kept, dropped = generate(SEED, PRODUCT, writer, n=5)
    assert [q.purpose for q in kept] == ["constraint", "use case", "language"]
    assert kept[2].locale == Locale("BR", "pt-BR")
    assert dropped == [
        "is Modelado good for photo to 3D?",
        "see alegauss.github.io/modelado for 3D",
    ]
    assert "Runs without an NVIDIA GPU: Yes" in writer.prompts[0]
    assert "Never name the product" in writer.prompts[0]


def _round(texts):
    results = [
        Result("openai", "m", i, answer=Answer("openai", "m", t, {}))
        for i, t in enumerate(texts, 1)
    ]
    return Round("q", NOW, results, runs=len(texts))


def test_score_and_rank():
    generic = _round(["1. Modly\n2. Meshroom", "1. Modly"])
    no_nvidia = _round(["1. Modelado\n2. Modly", "1. Modly\n2. Modelado"])
    prose = _round(["Try Modelado.", "1. Modly"])
    assert score(no_nvidia, ["Modelado"])[0] == (1 + 0.5) / 2
    assert score(prose, ["Modelado"])[0] == 0.25
    assert score(generic, ["Modelado"])[0] == 0
    questions = [Question("generic"), Question("no nvidia"), Question("prose")]
    ranked = rank(questions, [generic, no_nvidia, prose], ["Modelado"])
    assert [r.question.text for r in ranked] == ["no nvidia", "prose", "generic"]
    assert ranked[0].best == 1


class Discovering(FakePost):
    """Writes the variants, and answers: Modelado first when NVIDIA is ruled out."""

    def __call__(self, url, headers, body, timeout):
        if body and "text" in body and "format" in body["text"]:
            self.calls.append((url, headers, body))
            message = {"type": "output_text", "text": json.dumps(VARIANTS)}
            return {"output": [{"type": "message", "content": [message]}]}
        if "api.openai.com/v1/responses" in url:
            asked = body["input"]
            text = "1. Modelado\n2. Modly" if "NVIDIA" in asked else "1. Modly\n2. Meshroom"
            message = {"type": "output_text", "text": text}
            return {"output": [{"type": "message", "content": [message]}]}
        return super().__call__(url, headers, body, timeout)


def test_discover_ranks_the_no_nvidia_variant_above_the_generic(all_keys, tmp_path, capsys):
    argv = ["discover", str(EXAMPLE), "--seed", SEED, "--provider", "openai"]
    code = main([*argv, "--out", str(tmp_path)], post=Discovering())
    out = capsys.readouterr().out
    assert code == 0
    rows = [line for line in out.splitlines() if line.startswith("| ") and "rank" not in line]
    assert "photo to 3D on Windows without an NVIDIA GPU" in rows[0]
    assert rows[0].startswith("| 1 | 1.00 |")
    assert any(SEED in row and "| 0.00 |" in row for row in rows)
    assert "Dropped for naming the product or carrying personal data: is Modelado good" in out
    assert list(tmp_path.glob("*/*/discovery.md"))


def test_discover_needs_a_writer(no_keys, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "p")
    post = FakePost()
    assert main(["discover", str(EXAMPLE), "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
