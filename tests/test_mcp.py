"""AR24: an agent asks other assistants through the MCP server, without the user."""

from __future__ import annotations

import io
import json

from conftest import FakePost

from askround import mcp


def _call(name, arguments, tmp_path, post=None):
    message = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    reply = mcp.handle(message, str(tmp_path), post)
    result = reply["result"]
    return result["isError"], result["content"][0]["text"]


def test_initialize_and_list_the_tools():
    reply = mcp.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        }
    )
    assert reply["result"]["serverInfo"]["name"] == "askround"
    assert reply["result"]["capabilities"] == {"tools": {}}
    assert mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    tools = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    names = [t["name"] for t in tools]
    assert names == [
        "askround_ask",
        "askround_answer",
        "askround_run",
        "askround_job",
        "askround_research",
        "askround_report",
        "askround_diff",
        "askround_doctor",
    ]
    assert all(t["inputSchema"]["type"] == "object" for t in tools)


def test_an_agent_asks_two_providers_and_reads_an_answer(all_keys, tmp_path):
    arguments = {
        "question": "best free photo to 3D app on Windows?",
        "providers": ["openai", "gemini"],
        "runs": 1,
        "products": ["Modelado,modelado.app"],
    }
    failed, text = _call("askround_ask", arguments, tmp_path, FakePost())
    assert not failed
    data = json.loads(text)
    # the answers' text is not in the brief (law L1)
    assert "OpenAI says Modelado." not in text
    assert data["answers"] == 2
    product = data["products"][0]
    assert product["named"] == {"openai": "1/1", "gemini": "0/1"}
    assert product["in"] == ["openai#1"]
    failed, text = _call(
        "askround_answer", {"round": data["round"], "answer": product["in"][0]}, tmp_path
    )
    assert not failed
    one = json.loads(text)
    assert one["answer"] == "openai#1"
    assert one["text"] == "OpenAI says Modelado."
    assert one["sources"][0]["url"] == "https://modelado.app/"
    # the old way, by provider and run, still works
    failed, text = _call(
        "askround_answer", {"round": data["round"], "provider": "gemini", "run": 1}, tmp_path
    )
    assert json.loads(text)["text"] == "Gemini says Blender."
    failed, text = _call("askround_ask", {**arguments, "detail": True}, tmp_path, FakePost())
    assert "frequency" in json.loads(text)["report"]["products"][0]


def test_refusals_hold_for_an_agent(all_keys, tmp_path):
    post = FakePost()
    failed, text = _call(
        "askround_ask",
        {"question": "Is Modelado good?", "products": ["Modelado"]},
        tmp_path,
        post,
    )
    assert failed
    assert "names the product it tests" in text
    failed, text = _call("askround_ask", {"question": "q", "max_cost": 0.0001}, tmp_path, post)
    assert failed
    assert "above the cap" in text
    assert post.calls == []


def test_doctor_never_shows_a_key(all_keys, tmp_path):
    failed, text = _call("askround_doctor", {}, tmp_path, FakePost())
    assert not failed
    assert "OPENAI_API_KEY" in text
    assert "sk-test" not in text


def test_report_of_the_latest_round(all_keys, tmp_path):
    _call(
        "askround_ask", {"question": "q", "providers": ["openai"], "runs": 1}, tmp_path, FakePost()
    )
    failed, text = _call("askround_report", {}, tmp_path)
    assert not failed
    assert json.loads(text)["question"] == "q"


def test_unknown_tool_and_method():
    reply = mcp.handle(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nope"}}
    )
    assert reply["result"]["isError"] is True
    reply = mcp.handle({"jsonrpc": "2.0", "id": 4, "method": "resources/list"})
    assert reply["error"]["code"] == -32601


def test_serve_speaks_newline_delimited_json():
    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
        '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
        "not json\n"
        '{"jsonrpc":"2.0","id":2,"method":"ping"}\n'
    )
    stdout = io.StringIO()
    mcp.serve(stdin, stdout)
    replies = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [r.get("id") for r in replies] == [1, None, 2]
    assert replies[1]["error"]["code"] == -32700
    assert replies[2]["result"] == {}
