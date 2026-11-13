"""AR15: claims checked against a product file's facts, gaps pointing at the page that
should say the fact plainly.

The answer is SYNTHETIC, in the shape the 12/11/2026 notes describe ('CPU only: Check
build' for Modelado, which runs on the CPU).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import FakePost

from askround.cli import main
from askround.extract import verify_claims
from askround.gaps import compare
from askround.product import Fact, Product, load
from askround.providers import Answer, Source
from askround.report import build, find_round, load_round, markdown
from askround.round import Result, Round

NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=UTC)

FILE = """[product]
name = "Modelado"
aliases = []
places = ["alegauss.com/modelado", "github.com/alegauss/modelado"]

[[fact]]
attribute = "Runs without an NVIDIA GPU"
value = "Yes: on the CPU, or any DirectML GPU"
page = "https://alegauss.com/modelado/"

[[fact]]
attribute = "Price"
value = "Free"
page = "https://alegauss.com/modelado/"
"""

TABLE = "| App | CPU only | Price |\n|---|---|---|\n| Modelado | Check build | Free |\n"
CLAIMS = [
    {
        "product": "Modelado",
        "attribute": "CPU only",
        "value": "Check build",
        "quote": "Check build",
    },
    {
        "product": "Modelado",
        "attribute": "Price",
        "value": "Free",
        "quote": "Modelado | Check build | Free",
    },
]


@pytest.fixture
def product_file(tmp_path) -> Path:
    path = tmp_path / "modelado.toml"
    path.write_text(FILE, encoding="utf-8")
    return path


def test_load(product_file):
    product = load(product_file)
    assert product.name == "Modelado"
    assert product.names == [
        "Modelado",
        "alegauss.com/modelado",
        "github.com/alegauss/modelado",
    ]
    assert product.facts[0] == Fact(
        "Runs without an NVIDIA GPU",
        "Yes: on the CPU, or any DirectML GPU",
        "https://alegauss.com/modelado/",
    )


def test_load_refuses_a_bad_file(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("[product]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="needs a name"):
        load(bad)
    bad.write_text('[product]\nname = "X"\n[[fact]]\nattribute = "a"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="fact 1 needs"):
        load(bad)


class Judge:
    """Says claim 1 doubts fact 1 and claim 2 agrees with fact 2, and keeps the prompt."""

    name, model = "openai", "gpt-5-mini"

    def __init__(self):
        self.prompts = []

    def ask_json(self, prompt, schema):
        self.prompts.append(prompt)
        return {
            "verdicts": [
                {"claim": 1, "fact": 1, "verdict": "doubts", "why": "it says to check"},
                {"claim": 2, "fact": 2, "verdict": "agrees", "why": "free"},
                {"claim": 9, "fact": 1, "verdict": "contradicts", "why": "no such claim"},
            ]
        }


def _round():
    answer = Answer(
        "openai",
        "m",
        TABLE,
        {},
        sources=[Source("https://github.com/alegauss/modelado", "repo")],
    )
    answer.recommendations = []
    answer.claims = verify_claims(TABLE, CLAIMS)
    return Round("q", NOW, [Result("openai", "m", 1, answer=answer)], runs=1)


def test_the_cpu_gap_points_at_the_first_screen(product_file):
    judge = Judge()
    found = compare(_round(), load(product_file), judge)
    assert len(found) == 1  # the agreeing claim and the out-of-range verdict are not gaps
    gap = found[0]
    assert (gap.attribute, gap.value, gap.verdict) == ("CPU only", "Check build", "doubts")
    assert gap.fact == "Runs without an NVIDIA GPU: Yes: on the CPU, or any DirectML GPU"
    assert gap.page == "https://alegauss.com/modelado/"
    assert gap.cited == ["https://github.com/alegauss/modelado"]
    assert gap.providers == {"openai": 1}
    assert '1. CPU only: Check build (passage: "Check build")' in judge.prompts[0]


def test_nothing_to_compare_makes_no_call():
    judge = Judge()
    assert compare(_round(), Product("Modelado"), judge) == []
    assert judge.prompts == []


class Routed(FakePost):
    def __call__(self, url, headers, body, timeout):
        if body and "text" in body and "format" in body["text"]:
            self.calls.append((url, headers, body))
            if "verdicts" in json.dumps(body["text"]["format"]["schema"]):
                data = {"verdicts": [{"claim": 1, "fact": 1, "verdict": "doubts", "why": "hedges"}]}
            else:
                data = {"recommendations": [], "claims": CLAIMS[:1]}
            message = {"type": "output_text", "text": json.dumps(data)}
            return {"output": [{"type": "message", "content": [message]}]}
        if "api.openai.com/v1/responses" in url:
            message = {"type": "output_text", "text": TABLE}
            return {"output": [{"type": "message", "content": [message]}]}
        return super().__call__(url, headers, body, timeout)


def test_cli_product_file_reports_the_gap(all_keys, tmp_path, product_file, capsys):
    argv = ["ask", "q", "--provider", "openai", "--runs", "1", "--extract", "openai"]
    argv += ["--product-file", str(product_file), "--out", str(tmp_path / "rounds")]
    code = main(argv, post=Routed())
    out = capsys.readouterr().out
    assert code == 0
    assert "Modelado: fact gaps" in out
    assert "CPU only: Check build   (openai 1)  doubts" in out
    assert "say it plainly on https://alegauss.com/modelado/" in out
    round_, products = load_round(find_round(None, tmp_path / "rounds"))
    report = markdown(build(round_, products))
    assert "**Fact gaps**" in report
    assert "| CPU only: Check build | openai 1 | doubts |" in report


def test_a_bad_product_file_is_refused_before_the_round(all_keys, tmp_path, capsys):
    post = FakePost()
    argv = ["ask", "q", "--product-file", str(tmp_path / "missing.toml"), "--out", str(tmp_path)]
    assert main(argv, post=post) == 2
    assert post.calls == []
