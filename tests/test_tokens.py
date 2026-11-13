"""AR37: what each MCP tool's response costs an agent, against a budget per tool.

Every MCP tool is run on recorded rounds (`tests/fixtures/`, real answers from a live
round) and its response is counted, against the budget written in
`budgets/mcp-tokens.json`. A response over its budget fails: a field added to a response
is paid by every agent on every call, so raising a budget is a change to review, not a
side effect. Tokens are estimated as one per four characters of the response's JSON, the
usual rule of thumb for English text and JSON; the figures are approximations of a
tokenizer's, the same way for every tool.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from conftest import FakePost

from askround import mcp

ROOT = Path(__file__).parent.parent
BUDGETS = json.loads((ROOT / "budgets" / "mcp-tokens.json").read_text(encoding="utf-8"))
FIXTURES = Path(__file__).parent / "fixtures"
OPENAI = json.loads((FIXTURES / "openai-without-nvidia.json").read_text(encoding="utf-8"))
GEMINI = json.loads((FIXTURES / "gemini-without-nvidia.json").read_text(encoding="utf-8"))
READING = json.loads((FIXTURES / "openai-without-nvidia.reading.json").read_text(encoding="utf-8"))
QUESTION = READING["question"]


def tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


class Recorded(FakePost):
    """The providers answer with the recorded live responses; the extraction pass reads
    with the recorded reading."""

    def __call__(self, url, headers, body, timeout):
        if body and "text" in body and "format" in body["text"]:
            props = body["text"]["format"]["schema"]["properties"]
            if "recommendations" in props:
                data = {"recommendations": READING["recommendations"], "claims": []}
            elif "statements" in props:
                data = {"statements": []}
            else:
                data = {"claims": [], "disagreements": []}
            message = {"type": "output_text", "text": json.dumps(data)}
            return {"output": [{"type": "message", "content": [message]}]}
        if "api.openai.com" in url and body is not None:
            return OPENAI
        if "generativelanguage" in url and body is not None:
            return GEMINI
        return super().__call__(url, headers, body, timeout)


@pytest.fixture
def measured(all_keys, tmp_path):
    """Every tool's response on one realistic run, by tool name."""
    out = str(tmp_path)
    post = Recorded()
    two = ["openai", "gemini"]
    product = ["Modelado,alegauss.com/modelado"]
    asked = {
        "question": QUESTION,
        "providers": two,
        "runs": 3,
        "extract": True,
        "products": product,
    }
    calls = {
        "askround_ask": asked,
        "askround_ask detail": {**asked, "fresh": True, "detail": True},
        "askround_research": {"question": QUESTION, "providers": two},
        "askround_run": {
            "file": str(ROOT / "examples" / "modelado.toml"),
            "providers": two,
            "runs": 1,
        },
        "askround_doctor": {},
    }
    found = {}
    for name, arguments in calls.items():
        tool = name.split()[0]
        reply = mcp.call(tool, arguments, out, post)
        assert reply["isError"] is False, (name, reply["content"][0]["text"][:300])
        found[name] = reply["content"][0]["text"]
    brief = json.loads(found["askround_ask"])
    first, second = json.loads(found["askround_ask detail"])["round"], brief["round"]
    for name, arguments in {
        "askround_report": {"round": brief["round"]},
        "askround_diff": {"old": second, "new": first},
    }.items():
        reply = mcp.call(name, arguments, out)
        assert reply["isError"] is False, (name, reply["content"][0]["text"][:300])
        found[name] = reply["content"][0]["text"]
    one = {"round": brief["round"], "answer": brief["products"][0]["in"][0]}
    found["askround_answer"] = mcp.call("askround_answer", one, out)["content"][0]["text"]
    around = {**one, "around": READING["recommendations"][0]["quote"]}
    found["askround_answer around"] = mcp.call("askround_answer", around, out)["content"][0]["text"]
    return found


def test_every_tool_has_a_budget(measured):
    assert set(measured) == set(BUDGETS["tools"])


def test_every_response_fits_its_budget(measured):
    over = {
        name: (tokens(text), BUDGETS["tools"][name])
        for name, text in measured.items()
        if tokens(text) > BUDGETS["tools"][name]
    }
    assert not over, f"over budget (tokens, budget): {over}"


def test_the_brief_is_a_small_fraction_of_the_answers(measured):
    # law L1: the agent reads the brief, not the round
    assert tokens(measured["askround_ask"]) * 4 < tokens(measured["askround_ask detail"])


def test_print_the_figures(measured, capsys):
    """`pytest -s -k figures` prints the table the README publishes."""
    with capsys.disabled():
        for name, text in sorted(measured.items()):
            print(f"{name:26} {tokens(text):6} tokens  (budget {BUDGETS['tools'][name]})")
