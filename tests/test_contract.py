"""AR32: every command's JSON names its schema and validates against it; every fact in a
round resolves to its passage; the exit codes are the contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import FakePost
from schema_check import check

from askround.cli import main

EXAMPLE = Path(__file__).parent.parent / "examples" / "modelado.toml"
TEXT = "| App | CPU only |\n|---|---|\n| Modelado | Check build |\n\n1. Modelado\n2. Modly\n"


def _message(text):
    return {"type": "output_text", "text": text}


class World(FakePost):
    """Answers with TEXT, reads recommendations and a claim from it, merges research,
    writes discovery variants, and knows Modly on GitHub."""

    def __call__(self, url, headers, body, timeout):
        if "api.github.com" in url:
            self.calls.append((url, headers, body))
            return {
                "items": [
                    {
                        "name": "Modly",
                        "full_name": "x/Modly",
                        "html_url": "https://github.com/x/Modly",
                        "stargazers_count": 50,
                    }
                ]
            }
        if body and "text" in body and "format" in body["text"]:
            self.calls.append((url, headers, body))
            props = body["text"]["format"]["schema"]["properties"]
            if "recommendations" in props:
                data = {
                    "recommendations": [
                        {"name": "Modelado", "quote": "1. Modelado"},
                        {"name": "Modly", "quote": "2. Modly"},
                    ],
                    "claims": [
                        {
                            "product": "Modelado",
                            "attribute": "CPU only",
                            "value": "Check build",
                            "quote": "Modelado | Check build",
                        }
                    ],
                }
            elif "statements" in props:
                data = {"statements": [{"statement": "Modelado exists", "quote": "1. Modelado"}]}
            elif "questions" in props:
                data = {
                    "questions": [
                        {"text": "photo to 3D without NVIDIA", "axis": "constraint", "locale": ""}
                    ]
                }
            else:
                data = {
                    "claims": [{"claim": "Modelado exists", "ids": ["openai#1:1"]}],
                    "disagreements": [],
                }
            return {"output": [{"type": "message", "content": [_message(json.dumps(data))]}]}
        if "api.openai.com/v1/responses" in url:
            self.calls.append((url, headers, body))
            return {"model": "gpt-5", "output": [{"type": "message", "content": [_message(TEXT)]}]}
        return super().__call__(url, headers, body, timeout)


def _json(argv, capsys, post=None):
    code = main(argv, post=post or World())
    out = capsys.readouterr().out
    assert code == 0, out
    return json.loads(out)


@pytest.fixture
def rounds(all_keys, tmp_path, capsys):
    """Two rounds of the same question, read with the extraction pass."""
    argv = ["ask", "photo to 3D?", "--provider", "openai", "--runs", "2", "--extract", "openai"]
    argv += ["--product", "Modelado,modelado.app", "--json", "--out", str(tmp_path)]
    first = _json(argv, capsys)
    _json([*argv, "--fresh"], capsys)  # a second round, not the first one reused
    return tmp_path, first


def test_ask_json_validates_and_every_fact_reaches_its_passage(rounds):
    _, data = rounds
    assert check(data) == []
    texts = {(r["provider"], r["run"]): r["text"] for r in data["results"]}
    product = data["products"][0]
    for row in product["providers"]:
        for fact in row["in"]:
            provider, run = fact["answer"].split("#")
            start, end = fact["range"]
            assert "Modelado" in texts[(provider, int(run))][start:end]
    for claim in product["claims"]:
        for fact in claim["in"]:
            provider, run = fact["answer"].split("#")
            start, end = fact["range"]
            assert texts[(provider, int(run))][start:end] == claim["quote"]


def test_every_read_command_validates(rounds, capsys):
    out, _ = rounds
    where = ["--out", str(out)]
    assert check(_json(["report", "--json", *where], capsys)) == []
    assert check(_json(["report", "--brief", *where], capsys)) == []
    assert check(_json(["diff", "--json", *where], capsys)) == []
    assert check(_json(["series", "--product", "Modelado", "--json", *where], capsys)) == []
    assert (
        check(_json(["export", "--product", "Modelado", "--format", "json", *where], capsys)) == []
    )


def test_every_paid_command_validates(all_keys, tmp_path, capsys):
    where = ["--out", str(tmp_path)]
    assert check(_json(["doctor", "--json", "--no-check"], capsys)) == []
    assert check(_json(["lookup", "Modly", "--no-web", "--json"], capsys)) == []
    research = ["research", "q?", "--provider", "openai", "--extract", "openai", "--json", *where]
    assert check(_json(research, capsys)) == []
    run = ["run", str(EXAMPLE), "--provider", "openai", "--runs", "1", "--json", *where]
    assert check(_json(run, capsys)) == []
    discover = [
        "discover",
        str(EXAMPLE),
        "--provider",
        "openai",
        "--extract",
        "openai",
        "--json",
        *where,
    ]
    assert check(_json(discover, capsys)) == []


def test_the_checker_catches_a_broken_output(rounds):
    _, data = rounds
    broken = {**data, "schema": "askround/round@1", "runs": "two"}
    del broken["results"]
    found = check(broken)
    assert any("missing 'results'" in e for e in found)
    assert any("$.runs" in e for e in found)


def test_exit_codes(all_keys, tmp_path, capsys):
    where = ["--out", str(tmp_path), "--runs", "1", "--fresh"]
    assert main(["ask", "q", "--provider", "openai", *where], post=FakePost()) == 0
    partial = FakePost(fail={"api.anthropic.com": 404})
    assert (
        main(["ask", "q", "--provider", "openai", "--provider", "anthropic", *where], post=partial)
        == 3
    )
    failed = FakePost(fail={"api.openai.com": 404})
    assert main(["ask", "q", "--provider", "openai", *where], post=failed) == 1
    assert main(["ask", "jane@example.com?", *where], post=FakePost()) == 2
