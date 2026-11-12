"""AR12: one command turns a stored round into a short report, Markdown or JSON."""

from __future__ import annotations

import json

import pytest
from conftest import FakePost

from askround.cli import main
from askround.report import build, find_round, load_round, markdown


class Routed(FakePost):
    """The round's canned answers, and an extraction that reads one recommendation and
    one claim from the canned OpenAI answer."""

    def __call__(self, url, headers, body, timeout):
        if body and "text" in body and "format" in body["text"]:
            self.calls.append((url, headers, body))
            reading = {
                "recommendations": [{"name": "Modelado", "quote": "OpenAI says Modelado"}],
                "claims": [
                    {
                        "product": "Modelado",
                        "attribute": "Said by",
                        "value": "OpenAI",
                        "quote": "OpenAI says Modelado",
                    }
                ],
            }
            message = {"type": "output_text", "text": json.dumps(reading)}
            return {"output": [{"type": "message", "content": [message]}]}
        return super().__call__(url, headers, body, timeout)


@pytest.fixture
def stored(all_keys, tmp_path, capsys):
    argv = ["ask", "Best app?", "--provider", "openai", "--provider", "gemini", "--runs", "2"]
    argv += ["--product", "Modelado,modelado.app", "--extract", "openai", "--out", str(tmp_path)]
    assert main(argv, post=Routed()) == 0
    capsys.readouterr()
    return tmp_path


def test_a_stored_round_reads_back_the_same(stored):
    round_, products = load_round(find_round(None, stored))
    assert products == [["Modelado", "modelado.app"]]
    assert round_.question == "Best app?"
    assert round_.runs == 2
    first = round_.results[0].answer
    assert first.served_model == "gpt-5-2025-08-07"
    assert first.recommendations[0].name == "Modelado"
    assert first.claims[0].attribute == "Said by"


def test_report_json(stored, capsys):
    assert main(["report", "--out", str(stored), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    product = data["products"][0]
    openai = product["frequency"][0]
    assert (openai["provider"], openai["named"], openai["runs"]) == ("openai", 2, 2)
    assert openai["positions"] == [1, 1]
    assert openai["ranked_by"] == ["extraction", "extraction"]
    assert product["claims"][0]["value"] == "OpenAI"
    assert product["cited"][0]["kinds"] == {"site": 2}
    assert data["extracted"] is True
    # the answers' text is not in the report
    assert "OpenAI says Modelado." not in json.dumps(data["products"])
    assert "text" not in json.dumps(data["rivals"])


def test_report_markdown(stored, capsys):
    assert main(["report", str(next(stored.glob("*/*")))]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Best app?\n")
    assert "API answers, not the chat apps." in out
    assert "| openai | 2/2 | #1*, #1* | gpt-5-2025-08-07 |" in out
    assert "| gemini | 0/2 | -, - | gemini-2.5-flash |" in out
    assert "| Said by: OpenAI | openai 2 | OpenAI says Modelado |" in out
    assert "| openai | 2/2 | site 2 | 2x https://modelado.app/ |" in out


def test_report_for_another_product(stored, capsys):
    assert main(["report", "--out", str(stored), "--product", "Blender"]) == 0
    out = capsys.readouterr().out
    assert "## Blender" in out
    assert "## Modelado" not in out


def test_markdown_escapes_table_bars():
    report = {
        "question": "a | b",
        "asked_at": "2026-11-12T14:30:05+00:00",
        "runs": 1,
        "locales": [],
        "search": True,
        "answered": 0,
        "failed": [],
        "products": [],
        "rivals": {"read": 0, "missing": None, "top": [], "more": 0},
    }
    assert markdown(report).startswith("# a \\| b")


def test_no_round_is_an_error(tmp_path, capsys):
    assert main(["report", "--out", str(tmp_path)]) == 2
    assert "no round under" in capsys.readouterr().err


def test_build_reports_failures(all_keys, tmp_path, capsys):
    post = FakePost(fail={"generativelanguage.googleapis.com": 404})
    argv = ["ask", "q", "--provider", "openai", "--provider", "gemini", "--runs", "1"]
    main([*argv, "--out", str(tmp_path)], post=post)
    capsys.readouterr()
    round_, _ = load_round(find_round(None, tmp_path))
    data = build(round_, [])
    assert data["failed"][0]["provider"] == "gemini"
    assert "## Failed" in markdown(data)
