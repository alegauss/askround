"""A round: one question sent to several providers, several times each, kept on disk.

Assistants vary from one run to the next, so a round asks each provider the same
question `runs` times (default 3), each in a fresh conversation, and a product is
reported as the share of runs that named it and the positions it held, never as one
answer's verdict.

A round is saved as one directory, `<out>/<YYYY-MM-DD>/<HHMMSS>-<slug>/`, holding
`round.json` (the question, when it was asked, whether search was on, how many runs,
per answer what produced it - provider, run, requested and served model, search tool,
temperature, locale, the request settings and when it answered - then its text, search
queries and sources or its error, and the frequency of each product asked about) and
one `<provider>-<run>.json` per answer (`<provider>-<COUNTRY>-<run>.json` when the round
is asked in a locale) with the raw response exactly as the provider returned it. The
raw file is the evidence: everything askround later reads out of an answer is
re-derivable from it.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from askround import mention
from askround.http import HttpError
from askround.providers import Answer, Locale, Provider

DEFAULT_RUNS = 3
MAX_PARALLEL = 12


@dataclass
class Result:
    provider: str
    model: str
    run: int = 1
    answer: Answer | None = None
    error: str | None = None
    locale: Locale | None = None

    @property
    def ok(self) -> bool:
        return self.answer is not None


@dataclass
class Round:
    question: str
    asked_at: datetime
    results: list[Result] = field(default_factory=list)
    search: bool = True
    runs: int = 1
    locales: list[Locale] = field(default_factory=list)


@dataclass
class Frequency:
    """How one provider's runs, in one locale, answered by one model, named one
    product."""

    provider: str
    model: str
    runs: int
    named: int
    positions: list[int | None]
    locale: Locale | None = None
    # per run: "text" or "extraction", and the passage that ranked it ("" if none)
    ranked_by: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    @property
    def share(self) -> str:
        return f"{self.named}/{self.runs}"


def run_round(
    question: str,
    providers: list[Provider],
    now: datetime | None = None,
    search: bool = True,
    runs: int = DEFAULT_RUNS,
    locales: list[Locale] | None = None,
) -> Round:
    """Ask every provider `runs` times in each locale (or once with none), in parallel.
    A failure costs its answer only."""
    if runs < 1:
        raise ValueError("runs must be at least 1")
    asked_at = now or datetime.now(timezone.utc)
    places: list[Locale | None] = list(locales) if locales else [None]
    jobs = [
        (provider, place, run)
        for provider in providers
        for place in places
        for run in range(1, runs + 1)
    ]

    def ask(job: tuple[Provider, Locale | None, int]) -> Result:
        provider, place, run = job
        try:
            answer = provider.ask(question, search=search, locale=place)
        except Exception as error:  # noqa: BLE001 - any failure is recorded, never raised
            return Result(provider.name, provider.model, run, error=describe(error), locale=place)
        return Result(provider.name, answer.model, run, answer=answer, locale=place)

    with ThreadPoolExecutor(max_workers=max(1, min(len(jobs), MAX_PARALLEL))) as pool:
        results = list(pool.map(ask, jobs))
    return Round(question, asked_at, results, search=search, runs=runs, locales=list(locales or []))


def describe(error: BaseException) -> str:
    """The error as a round records it, with the attempts it took when retried.
    An HTTP error's body is cut short: some providers echo part of the request."""
    if isinstance(error, HttpError):
        text = f"HttpError: HTTP {error.status}: {' '.join(error.body.split())[:200]}"
    else:
        text = f"{type(error).__name__}: {error}"
    attempts = getattr(error, "attempts", 1)
    return f"{text} (after {attempts} attempts)" if attempts > 1 else text


def failures(round_: Round) -> list[Result]:
    return [r for r in round_.results if r.answer is None]


def frequency(round_: Round, names: list[str]) -> list[Frequency]:
    """Per provider, locale and served model, in the round's order: the runs that
    answered, how many named the product, and its position in each (None where unnamed
    or named outside a list). Grouping by the model that answered keeps a silent model
    update apart from a change in the product, and by locale lets two countries be read
    side by side. A failed run is not counted, so 2/2 after a failure is not passed off
    as 2/3; a provider and locale with no answer get one 0/0 row."""
    table: dict[tuple[str, Locale | None, str], Frequency] = {}
    slots: dict[tuple[str, Locale | None], str] = {}
    for r in round_.results:
        slots.setdefault((r.provider, r.locale), r.model)
        if r.answer is None:
            continue
        served = r.answer.served_model or r.answer.model
        row = table.setdefault(
            (r.provider, r.locale, served),
            Frequency(r.provider, served, 0, 0, [], locale=r.locale),
        )
        found = mention.locate(r.answer, names)
        row.runs += 1
        row.named += found.named
        row.positions.append(found.position)
        row.ranked_by.append(found.by)
        row.evidence.append(found.evidence)
    for (provider, place), model in slots.items():
        if not any(key[:2] == (provider, place) for key in table):
            table[(provider, place, model)] = Frequency(provider, model, 0, 0, [], locale=place)
    order = list(slots)
    return sorted(table.values(), key=lambda f: order.index((f.provider, f.locale)))


def summary(round_: Round, products: list[list[str]] | None = None) -> dict:
    """The round as `round.json` holds it: everything but the raw responses."""
    data = {
        "question": round_.question,
        "asked_at": round_.asked_at.astimezone(timezone.utc).isoformat(),
        "search": round_.search,
        "runs": round_.runs,
        "locales": [_locale(place) for place in round_.locales],
        "answered": len(round_.results) - len(failures(round_)),
        "failed": len(failures(round_)),
        "results": [_result(r) for r in round_.results],
    }
    if products:
        data["products"] = [
            {
                "product": names[0],
                "names": names,
                "providers": [
                    {
                        "provider": f.provider,
                        "locale": str(f.locale) if f.locale else None,
                        "model": f.model,
                        "runs": f.runs,
                        "named": f.named,
                        "positions": f.positions,
                        "ranked_by": f.ranked_by,
                        "evidence": f.evidence,
                    }
                    for f in frequency(round_, names)
                ],
            }
            for names in products
        ]
    return data


def _locale(place: Locale | None, ignored: list[str] | None = None) -> dict | None:
    if place is None:
        return None
    data: dict = {"country": place.country, "language": place.language}
    if ignored is not None:
        data["ignored"] = ignored
    return data


def _result(r: Result) -> dict:
    """One answer and what produced it. `temperature` is null where askround left it
    to the provider's default, `locale` where none was asked for; `locale.ignored`
    names what the provider's API could not take."""
    answer = r.answer
    if answer is None:
        # the same keys as an answer, so a reader never branches on their presence
        return {
            "provider": r.provider,
            "run": r.run,
            "model": r.model,
            "served_model": None,
            "answered_at": None,
            "search": None,
            "search_tool": None,
            "temperature": None,
            "locale": _locale(r.locale),
            "settings": {},
            "text": None,
            "queries": [],
            "sources": [],
            "recommendations": None,
            "extracted_by": None,
            "extraction_error": None,
            "error": r.error,
        }
    settings = answer.settings
    return {
        "provider": r.provider,
        "run": r.run,
        "model": r.model,
        "served_model": answer.served_model,
        "answered_at": answer.answered_at.isoformat() if answer.answered_at else None,
        "search": answer.search,
        "search_tool": settings.get("tools"),
        "temperature": settings.get("temperature"),
        "locale": _locale(answer.locale, answer.locale_ignored),
        "settings": settings,
        "text": answer.text,
        "queries": answer.queries,
        "sources": [{"url": s.url, "title": s.title} for s in answer.sources],
        "recommendations": (
            None
            if answer.recommendations is None
            else [
                {"name": rec.name, "quote": rec.quote, "verified": rec.verified}
                for rec in answer.recommendations
            ]
        ),
        "extracted_by": answer.extracted_by or None,
        "extraction_error": answer.extraction_error,
        "error": None,
    }


def slug(text: str, limit: int = 40) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return words[:limit].rstrip("-") or "question"


def save_round(round_: Round, out: Path, products: list[list[str]] | None = None) -> Path:
    stamp = round_.asked_at.astimezone(timezone.utc)
    directory = (
        out / stamp.strftime("%Y-%m-%d") / f"{stamp.strftime('%H%M%S')}-{slug(round_.question)}"
    )
    directory.mkdir(parents=True, exist_ok=True)
    _write(directory / "round.json", summary(round_, products))
    for r in round_.results:
        if r.answer is not None:
            _write(directory / raw_name(r), r.answer.raw)
    return directory


def raw_name(r: Result) -> str:
    """`<provider>-<run>.json`, or `<provider>-<COUNTRY>-<run>.json` in a locale."""
    place = f"-{r.locale.country}" if r.locale else ""
    return f"{r.provider}{place}-{r.run}.json"


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
