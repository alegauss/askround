"""AR34: the person sets the budget; a round past it waits for their approval, and the
spending comes back with every paid result."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from conftest import FakePost

from askround import budget, mcp
from askround.cli import main


def _set_budget(day: float | None = None, month: float | None = None) -> Path:
    path = Path(os.environ["ASKROUND_CONFIG"])
    lines = ["[budget]"]
    if day is not None:
        lines.append(f"day = {day}")
    if month is not None:
        lines.append(f"month = {month}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_the_ledger_sums_today_and_this_month(tmp_path):
    budget.record(tmp_path, 0.10, "q", now=datetime(2026, 11, 12, 9, tzinfo=UTC))
    budget.record(tmp_path, 0.20, "q", now=datetime(2026, 11, 12, 18, tzinfo=UTC))
    budget.record(tmp_path, 0.40, "q", now=datetime(2026, 11, 3, tzinfo=UTC))
    budget.record(tmp_path, 9.00, "q", now=datetime(2026, 10, 30, tzinfo=UTC))
    assert budget.spent(tmp_path, now=datetime(2026, 11, 12, 20, tzinfo=UTC)) == (0.3, 0.7)


def test_no_config_means_no_budget(tmp_path):
    assert budget.load() == budget.Budget()
    assert budget.over(tmp_path, 100.0) is None


def test_a_saved_round_is_recorded(all_keys, tmp_path, capsys):
    main(
        ["ask", "q", "--provider", "openai", "--runs", "1", "--out", str(tmp_path)], post=FakePost()
    )
    assert (tmp_path / budget.LEDGER).is_file()


def test_an_agents_round_past_the_budget_asks_for_approval(all_keys, tmp_path):
    _set_budget(day=0.01)
    post = FakePost()
    reply = mcp.call("askround_ask", {"question": "best photo to 3D app?"}, str(tmp_path), post)
    assert reply["isError"] is True
    text = reply["content"][0]["text"]
    assert "[budget.over]" in text
    assert "needs the person's approval" in text
    assert "An agent asks the person; it cannot approve" in text
    assert post.calls == []  # no provider called
    # and the agent has no way to approve: no tool takes such a parameter
    assert all("approve" not in t["inputSchema"]["properties"] for t in mcp.TOOLS)


def test_the_person_approves_on_the_command_line(all_keys, tmp_path, capsys):
    _set_budget(day=0.01)
    argv = ["ask", "q", "--provider", "openai", "--runs", "1", "--out", str(tmp_path)]
    assert main(argv, post=FakePost()) == 2
    assert "[budget.over]" in capsys.readouterr().err
    assert main([*argv, "--approve"], post=FakePost()) == 0


def test_the_month_budget_counts_what_was_spent(all_keys, tmp_path, capsys):
    _set_budget(month=1.0)
    budget.record(tmp_path, 0.999, "earlier")
    argv = ["ask", "q", "--provider", "openai", "--runs", "1", "--out", str(tmp_path)]
    assert main(argv, post=FakePost()) == 2
    assert "this month $0.9990 spent" in capsys.readouterr().err


def test_spending_comes_back_with_every_paid_result(all_keys, tmp_path):
    _set_budget(day=50.0, month=200.0)
    budget.record(tmp_path, 0.25, "earlier")
    reply = mcp.call(
        "askround_ask",
        {"question": "q", "providers": ["openai"], "runs": 1},
        str(tmp_path),
        FakePost(),
    )
    assert reply["isError"] is False
    spending = json.loads(reply["content"][0]["text"])["spending"]
    assert spending["budget"] == {"day": 50.0, "month": 200.0}
    assert spending["month"] >= 0.25


def test_cli_budget_json_validates(tmp_path, capsys):
    from schema_check import check

    _set_budget(day=1.0)
    assert main(["budget", "--json", "--out", str(tmp_path)]) == 0
    assert check(json.loads(capsys.readouterr().out)) == []


def test_cli_budget(tmp_path, capsys):
    path = _set_budget(day=1.0, month=10.0)
    budget.record(tmp_path, 0.5, "q")
    assert main(["budget", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "spent today $0.5000 of $1.00; this month $0.5000 of $10.00" in out
    assert str(path) in out
