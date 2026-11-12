"""The person's budget: what askround may spend a day and a month, and what it has spent.

askround spends money on the user's keys, and an agent with the MCP tools can run rounds
on its own, in a loop. So the person sets a budget in askround's config file, which no
MCP tool writes (law L5: the person, never the agent, sets the money):

    # %APPDATA%\\askround\\config.toml on Windows, ~/.config/askround/config.toml
    # elsewhere, or the file ASKROUND_CONFIG names
    [budget]
    day = 1.00      # USD
    month = 10.00

Every saved round adds its actual cost to a ledger, `spent.jsonl` beside the rounds. A
run whose estimate would take the day's or the month's spending past the budget is not
run: it is refused before any call, with the estimate, the spending so far and the
budget, as a request for the person's approval. Only the person approves - with
`--approve` on the command line, which the MCP tools do not offer - or raises the budget.
Days and months are counted in UTC.
"""

from __future__ import annotations

import json
import os
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

LEDGER = "spent.jsonl"


@dataclass(frozen=True)
class Budget:
    day: float | None = None
    month: float | None = None


def config_path() -> Path:
    if os.environ.get("ASKROUND_CONFIG"):
        return Path(os.environ["ASKROUND_CONFIG"])
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "askround" / "config.toml"
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "askround" / "config.toml"


def load() -> Budget:
    path = config_path()
    if not path.is_file():
        return Budget()
    data = tomllib.loads(path.read_text(encoding="utf-8")).get("budget") or {}
    return Budget(_amount(data.get("day")), _amount(data.get("month")))


def _amount(value) -> float | None:
    return float(value) if isinstance(value, int | float) and value >= 0 else None


def record(out: Path, cost: float | None, question: str, now: datetime | None = None) -> None:
    """Add a saved round's actual cost to the ledger (a cost the table cannot price is 0)."""
    out.mkdir(parents=True, exist_ok=True)
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    entry = {"at": moment.isoformat(), "cost": round(cost or 0.0, 6), "question": question[:120]}
    with (out / LEDGER).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def spent(out: Path, now: datetime | None = None) -> tuple[float, float]:
    """USD spent today and this month, from the ledger."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    day, month = moment.strftime("%Y-%m-%d"), moment.strftime("%Y-%m")
    today = this_month = 0.0
    path = out / LEDGER
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry["at"][:7] == month:
                this_month += entry["cost"]
                if entry["at"][:10] == day:
                    today += entry["cost"]
    return round(today, 6), round(this_month, 6)


def status(out: Path, now: datetime | None = None) -> dict:
    """What has been spent against the budget; reported with every paid result."""
    today, month = spent(out, now)
    limits = load()
    return {
        "today": today,
        "month": month,
        "budget": {"day": limits.day, "month": limits.month},
        "config": str(config_path()),
    }


def over(out: Path, estimate: float, now: datetime | None = None) -> str | None:
    """Why this run would pass the budget, or None when it fits (or there is none)."""
    limits = load()
    today, month = spent(out, now)
    if limits.day is not None and today + estimate > limits.day:
        return f"today ${today:.4f} spent + ${estimate:.4f} estimated > the day's budget ${limits.day:.2f}"
    if limits.month is not None and month + estimate > limits.month:
        return f"this month ${month:.4f} spent + ${estimate:.4f} estimated > the month's budget ${limits.month:.2f}"
    return None
