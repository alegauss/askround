"""Reuse a recent round: the same question asked the same way again costs nothing.

An agent that lost a result from its context, or a second session on the same task,
asks the same question again, and each repeat would pay for every search again. So
before a round is asked, askround looks for one it already holds that answered the same
question the same way - the same text, providers and requested models, locales and web
search, at least as many answers from each provider (a round with failures is asked
again), and the extraction pass if this run wants it - within a freshness window, and
returns it, marked with its age, calling no provider.

The window is 24 hours unless the config file says otherwise:

    [reuse]
    max_age_hours = 24      # 0 turns reuse off

`--fresh` (or `fresh: true` over MCP) asks again; that run counts against the budget
like any other.
"""

from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from askround import budget

DEFAULT_HOURS = 24.0


def max_age_hours() -> float:
    path = budget.config_path()
    if path.is_file():
        value = (tomllib.loads(path.read_text(encoding="utf-8")).get("reuse") or {}).get(
            "max_age_hours"
        )
        if isinstance(value, int | float) and value >= 0:
            return float(value)
    return DEFAULT_HOURS


def find(
    out: Path,
    question: str,
    providers: list,
    runs: int,
    search: bool,
    locales: list,
    extract: bool,
    now: datetime | None = None,
) -> tuple[Path, float] | None:
    """The newest stored round that answers this one, and its age in hours; or None."""
    hours = max_age_hours()
    if hours <= 0:
        return None
    moment = now or datetime.now(UTC)
    wanted = {(p.name, p.model) for p in providers}
    places = sorted(str(x) for x in locales or [])
    found: list[tuple[datetime, Path]] = []
    for path in out.glob("*/*/round.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            asked = datetime.fromisoformat(data["asked_at"])
        except (OSError, ValueError, KeyError):
            continue
        fresh = 0 <= (moment - asked).total_seconds() / 3600 <= hours
        same = data.get("question") == question and data.get("search", True) == search
        if fresh and same and _answers(data, wanted, runs, places, extract):
            found.append((asked, path))
    if not found:
        return None
    asked, path = max(found)
    return path, round((moment - asked).total_seconds() / 3600, 2)


def _answers(data: dict, wanted: set, runs: int, places: list[str], extract: bool) -> bool:
    """Whether a stored round holds what this one would ask for."""
    if data.get("runs", 1) < runs:
        return False
    stored_places = sorted(
        f"{x['country']}:{x['language']}" if x.get("language") else x["country"]
        for x in data.get("locales") or []
    )
    if stored_places != places:
        return False
    # every provider asked for answered at least `runs` times in each locale: a round with
    # failures is asked again, since that is how the missing answers come back
    answered: dict[tuple[str, str], int] = {}
    for r in data.get("results") or []:
        if not r.get("error"):
            key = (r["provider"], r["model"])
            answered[key] = answered.get(key, 0) + 1
    if any(answered.get(w, 0) < runs * max(1, len(places)) for w in wanted):
        return False
    return not extract or any(r.get("recommendations") is not None for r in data["results"])
