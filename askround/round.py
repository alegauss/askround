"""A round: one question sent to several providers at once, kept on disk.

A round is saved as one directory, `<out>/<YYYY-MM-DD>/<HHMMSS>-<slug>/`, holding
`round.json` (the question, when it was asked, whether search was on, and per
provider its model, answer text, search queries and sources, or error) and one
`<provider>.json` per answer with the raw response exactly as the provider returned
it. The raw file is the evidence: everything askround later reads out of an answer is
re-derivable from it.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from askround.providers import Answer, Provider


@dataclass
class Result:
    provider: str
    model: str
    answer: Answer | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.answer is not None


@dataclass
class Round:
    question: str
    asked_at: datetime
    results: list[Result] = field(default_factory=list)
    search: bool = True


def run_round(
    question: str,
    providers: list[Provider],
    now: datetime | None = None,
    search: bool = True,
) -> Round:
    """Ask every provider in parallel. One provider failing costs its answer only."""
    asked_at = now or datetime.now(timezone.utc)

    def ask(provider: Provider) -> Result:
        try:
            answer = provider.ask(question, search=search)
        except Exception as error:  # noqa: BLE001 - any failure is recorded, never raised
            return Result(provider.name, provider.model, error=f"{type(error).__name__}: {error}")
        return Result(provider.name, answer.model, answer=answer)

    with ThreadPoolExecutor(max_workers=max(1, len(providers))) as pool:
        results = list(pool.map(ask, providers))
    return Round(question, asked_at, results, search=search)


def summary(round_: Round) -> dict:
    """The round as `round.json` holds it: everything but the raw responses."""
    return {
        "question": round_.question,
        "asked_at": round_.asked_at.astimezone(timezone.utc).isoformat(),
        "search": round_.search,
        "results": [
            {
                "provider": r.provider,
                "model": r.model,
                "text": r.answer.text if r.answer else None,
                "queries": r.answer.queries if r.answer else [],
                "sources": (
                    [{"url": s.url, "title": s.title} for s in r.answer.sources] if r.answer else []
                ),
                "error": r.error,
            }
            for r in round_.results
        ],
    }


def slug(text: str, limit: int = 40) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return words[:limit].rstrip("-") or "question"


def save_round(round_: Round, out: Path) -> Path:
    stamp = round_.asked_at.astimezone(timezone.utc)
    directory = (
        out / stamp.strftime("%Y-%m-%d") / f"{stamp.strftime('%H%M%S')}-{slug(round_.question)}"
    )
    directory.mkdir(parents=True, exist_ok=True)
    _write(directory / "round.json", summary(round_))
    for r in round_.results:
        if r.answer is not None:
            _write(directory / f"{r.provider}.json", r.answer.raw)
    return directory


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
