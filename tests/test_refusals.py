"""AR33: a bad round is refused before it is paid for, every problem at once, each with
a code, the change that passes it, and an explanation."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from conftest import FakePost

from askround import mcp, refusals
from askround.cli import main

CLI = Path(__file__).parent.parent / "plugin" / "src" / "askround" / "cli.py"


def test_every_problem_is_listed_at_once_and_nothing_is_sent(
    no_keys, monkeypatch, tmp_path, capsys
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    post = FakePost()
    question = "Is Modelado good? Mail jane@example.com"
    argv = ["ask", question, "--product", "Modelado", "--check-rivals", "--max-cost", "0.000001"]
    assert main([*argv, "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
    err = capsys.readouterr().err
    for code in ("question.personal-data", "question.leading", "extract.needed", "cost.over-cap"):
        assert f"[{code}]" in err
    assert "refused before anything was sent: 4 problem(s)" in err
    assert err.count("fix: ") == 4


@pytest.mark.parametrize(
    ("argv", "code"),
    [
        (["ask", "   "], "question.empty"),
        (["ask", "x" * (refusals.QUESTION_LIMIT + 1)], "question.too-long"),
        (["ask", "q", "--check-links"], "product.needed"),
        (["ask", "q", "--product-file", "missing.toml"], "product-file.invalid"),
        (["research", "call +55 11 91234-5678"], "question.personal-data"),
    ],
)
def test_each_case_is_refused_with_its_code(all_keys, tmp_path, capsys, argv, code):
    post = FakePost()
    assert main([*argv, "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
    assert f"[{code}]" in capsys.readouterr().err


def test_no_key_and_no_reader(no_keys, tmp_path, capsys):
    post = FakePost()
    assert main(["research", "q?", "--out", str(tmp_path)], post=post) == 2
    err = capsys.readouterr().err
    assert "[provider.no-key]" in err
    assert "[extract.no-reader]" in err


def test_every_code_used_is_explained():
    used = set(re.findall(r'add\(\s*"([a-z-]+\.[a-z-]+)"', CLI.read_text(encoding="utf-8")))
    assert used, "the CLI adds refusals"
    assert used <= set(refusals.CODES)
    for code, (meaning, fix) in refusals.CODES.items():
        assert meaning and fix, code
        assert refusals.explain(code).startswith(code)


def test_an_unknown_code_cannot_be_raised():
    with pytest.raises(KeyError):
        refusals.Checks().add("made.up", "x")


def test_cli_explain(capsys):
    assert main(["explain", "question.leading"]) == 0
    out = capsys.readouterr().out
    assert "brand question" in out
    assert main(["explain"]) == 0
    assert "cost.over-cap" in capsys.readouterr().out
    assert main(["explain", "made.up"]) == 2


def test_mcp_schemas_carry_the_limits(no_keys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    listed = {t["name"]: t for t in mcp.tools()}
    ask = listed["askround_ask"]["inputSchema"]["properties"]
    assert ask["question"]["maxLength"] == refusals.QUESTION_LIMIT
    assert ask["providers"]["items"]["enum"] == ["gemini"]
    # the static list is not changed by it
    assert "maxLength" not in mcp.TOOLS[0]["inputSchema"]["properties"]["question"]


def test_mcp_refusal_names_the_codes(all_keys, tmp_path):
    reply = mcp.call(
        "askround_ask",
        {"question": "Is Modelado good?", "products": ["Modelado"], "max_cost": 0.000001},
        str(tmp_path),
        FakePost(),
    )
    assert reply["isError"] is True
    text = reply["content"][0]["text"]
    assert "[question.leading]" in text and "[cost.over-cap]" in text
    json.dumps(reply)
