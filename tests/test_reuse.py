"""AR36: the same question asked again the same day returns the stored round, with its
date, and calls no provider."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import FakePost

from askround import mcp, reuse
from askround.cli import main
from askround.providers import by_name

ARGV = ["ask", "best photo to 3D app?", "--provider", "openai", "--runs", "2"]


def _first(tmp_path, capsys, *extra):
    post = FakePost()
    assert main([*ARGV, *extra, "--out", str(tmp_path)], post=post) == 0
    capsys.readouterr()
    return post


def test_a_repeat_returns_the_stored_round_and_calls_nothing(all_keys, tmp_path, capsys):
    _first(tmp_path, capsys)
    again = FakePost()
    assert main([*ARGV, "--json", "--out", str(tmp_path)], post=again) == 0
    data = json.loads(capsys.readouterr().out)
    assert again.calls == []
    assert data["reused"]["age_hours"] >= 0
    assert data["reused"]["from"] == data["asked_at"]
    assert len(data["results"]) == 2
    assert len(list(tmp_path.glob("*/*/round.json"))) == 1  # nothing new was saved


def test_the_person_sees_it_was_reused(all_keys, tmp_path, capsys):
    _first(tmp_path, capsys)
    main([*ARGV, "--out", str(tmp_path)], post=FakePost())
    assert capsys.readouterr().out.startswith("reused the round asked")


def test_fresh_asks_again(all_keys, tmp_path, capsys):
    _first(tmp_path, capsys)
    again = FakePost()
    assert main([*ARGV, "--fresh", "--out", str(tmp_path)], post=again) == 0
    assert len(again.calls) == 2
    assert len(list(tmp_path.glob("*/*/round.json"))) == 2


def test_only_the_same_round_is_reused(all_keys, tmp_path, capsys):
    _first(tmp_path, capsys)
    store = tmp_path
    providers = by_name(["openai"])
    question = "best photo to 3D app?"
    assert reuse.find(store, question, providers, 2, True, [], False)
    assert reuse.find(store, question, providers, 1, True, [], False), "fewer runs is fine"
    assert reuse.find(store, question, providers, 3, True, [], False) is None, "more runs is not"
    assert reuse.find(store, "another question?", providers, 2, True, [], False) is None
    assert reuse.find(store, question, by_name(["gemini"]), 2, True, [], False) is None
    assert reuse.find(store, question, providers, 2, False, [], False) is None, "search off"
    assert reuse.find(store, question, providers, 2, True, ["BR:pt-BR"], False) is None
    assert reuse.find(store, question, providers, 2, True, [], True) is None, "not extracted"


def test_a_round_with_failures_is_asked_again(all_keys, tmp_path, capsys):
    failing = FakePost(fail={"api.openai.com": 500})
    main([*ARGV, "--out", str(tmp_path)], post=failing)
    capsys.readouterr()
    again = FakePost()
    assert main([*ARGV, "--out", str(tmp_path)], post=again) == 0
    assert len(again.calls) == 2


def test_an_old_round_is_not_reused(all_keys, tmp_path, capsys):
    _first(tmp_path, capsys)
    later = datetime.now(UTC) + timedelta(hours=25)
    assert (
        reuse.find(
            tmp_path, "best photo to 3D app?", by_name(["openai"]), 2, True, [], False, now=later
        )
        is None
    )


def test_the_window_is_set_in_the_config(all_keys, tmp_path, capsys):
    _first(tmp_path, capsys)
    Path(os.environ["ASKROUND_CONFIG"]).write_text("[reuse]\nmax_age_hours = 0\n", encoding="utf-8")
    again = FakePost()
    main([*ARGV, "--out", str(tmp_path)], post=again)
    assert len(again.calls) == 2  # reuse off


def test_an_agent_gets_the_reused_brief(all_keys, tmp_path):
    arguments = {"question": "best photo to 3D app?", "providers": ["openai"], "runs": 2}
    mcp.call("askround_ask", arguments, str(tmp_path), FakePost())
    again = FakePost()
    reply = mcp.call("askround_ask", arguments, str(tmp_path), again)
    data = json.loads(reply["content"][0]["text"])
    assert again.calls == []
    assert data["schema"] == "askround/brief@1"
    assert "age_hours" in data["reused"]
    fresh = FakePost()
    mcp.call("askround_ask", {**arguments, "fresh": True}, str(tmp_path), fresh)
    assert len(fresh.calls) == 2
