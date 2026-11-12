"""AR31: a full round reaches the agent in a few hundred tokens, and any fact in it
reaches its passage with one more call."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from askround import mcp
from askround.extract import verify, verify_claims
from askround.providers import Answer, Locale
from askround.report import answer_id, brief
from askround.round import Result, Round, save_round

NOW = datetime(2026, 11, 12, tzinfo=UTC)
PROVIDERS = ("openai", "gemini", "anthropic", "perplexity")
TEXT = (
    "Here is a long answer with a table and many words. " * 60
    + "\n| App | CPU only | Verdict |\n|---|---|---|\n| Modelado | Check build | Best fit |\n"
    + "1. Modelado\n2. Modly\n3. Meshroom\n4. TripoSR\n5. Blender\n6. Hunyuan3D\n"
)


def _round() -> Round:
    """A full round: four providers, three runs each, every answer long and read."""
    results = []
    for provider in PROVIDERS:
        for run in (1, 2, 3):
            answer = Answer(provider, "m", TEXT, {})
            names = ["Modelado", "Modly", "Meshroom", "TripoSR", "Blender", "Hunyuan3D"]
            answer.recommendations = verify(TEXT, [{"name": n, "quote": n} for n in names])
            answer.claims = verify_claims(
                TEXT,
                [
                    {
                        "product": "Modelado",
                        "attribute": "CPU only",
                        "value": "Check build",
                        "quote": "Modelado | Check build",
                    }
                ],
            )
            results.append(Result(provider, "m", run, answer=answer))
    return Round("best photo to 3D app without NVIDIA?", NOW, results, runs=3)


def test_a_full_round_fits_in_a_few_hundred_tokens(tmp_path):
    round_ = _round()
    raw_chars = sum(len(r.answer.text) for r in round_.results)
    found = brief(round_, [["Modelado", "modelado.app"]], str(tmp_path))
    compact = json.dumps(found, ensure_ascii=False, separators=(",", ":"))
    # a token is about four characters; a few hundred tokens is under ~2,000 characters
    assert len(compact) < 2000, len(compact)
    assert raw_chars > 30 * len(compact)
    product = found["products"][0]
    assert product["named"]["openai"] == "3/3 #1"
    assert product["claims"][0]["c"] == "CPU only: Check build"
    assert len(product["claims"][0]["in"]) == 12
    assert [r["name"] for r in found["rivals"]] == [
        "Modly",
        "Meshroom",
        "TripoSR",
        "Blender",
        "Hunyuan3D",
    ]


def test_answer_ids():
    r = Result("openai", "m", 2, answer=Answer("openai", "m", "x", {}))
    assert answer_id(r) == "openai#2"
    r.locale = Locale("BR", "pt-BR")
    assert answer_id(r) == "openai@BR#2"


def test_a_fact_reaches_its_passage_with_one_call(tmp_path):
    round_ = _round()
    directory = save_round(round_, tmp_path, [["Modelado"]])
    found = brief(round_, [["Modelado"]], str(directory))
    claim = found["products"][0]["claims"][0]
    arguments = {"round": found["round"], "answer": claim["in"][0], "around": "Check build"}
    reply = mcp.call("askround_answer", arguments, str(tmp_path))
    assert reply["isError"] is False
    passage = json.loads(reply["content"][0]["text"])["passage"]
    assert "Modelado | Check build" in passage
    assert len(passage) < len(TEXT) / 3


def test_a_quote_not_in_the_answer_is_refused(tmp_path):
    directory = save_round(_round(), tmp_path, [["Modelado"]])
    arguments = {"round": str(directory), "answer": "openai#1", "around": "invented words"}
    reply = mcp.call("askround_answer", arguments, str(tmp_path))
    assert reply["isError"] is True


@pytest.mark.parametrize("bad", ["openai", "openai#x", "#2"])
def test_a_bad_answer_id_is_refused(tmp_path, bad):
    directory = save_round(_round(), tmp_path, [["Modelado"]])
    reply = mcp.call("askround_answer", {"round": str(directory), "answer": bad}, str(tmp_path))
    assert reply["isError"] is True


def test_cli_brief(tmp_path, capsys):
    from askround.cli import main

    save_round(_round(), tmp_path, [["Modelado"]])
    assert main(["report", "--brief", "--out", str(tmp_path)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["products"][0]["named"]["gemini"] == "3/3 #1"
