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
from datetime import UTC, datetime
from pathlib import Path

from askround import citations, costs, mention, series
from askround.claims import product_claims
from askround.http import HttpError
from askround.provenance import answer_id, schema, span
from askround.providers import Answer, Locale, Provider
from askround.rivals import key, rivals

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
    # a brand question names the product on purpose; its rounds are reported apart
    brand: bool = False
    # the prompt set (its product's name) and the question's purpose, when run from one
    set: str = ""
    purpose: str = ""
    # costs.py: the estimate made before the round, what the extraction pass's own calls
    # cost, and the actual cost per provider as stored (a round read back has no raw
    # responses to price again)
    estimate: dict | None = None
    extraction_cost: float | None = None
    spent: dict | None = None
    # whether each rival exists, by rivals.key(name), when --check-rivals ran (lookup.py)
    checks: dict = field(default_factory=dict)
    # the product's attributed links, followed, by product name, when --check-links ran
    links: dict = field(default_factory=dict)
    # claims that contradict or doubt a product file's facts, by product name (gaps.py)
    gaps: dict = field(default_factory=dict)


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
    # per run: the answer's id, and the characters that name or rank it (None if unnamed)
    answers: list[str] = field(default_factory=list)
    ranges: list[list[int] | None] = field(default_factory=list)

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
    asked_at = now or datetime.now(UTC)
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
        row.answers.append(answer_id(r))
        row.ranges.append(_where(r.answer.text, names, found) if found.named else None)
    for (provider, place), model in slots.items():
        if not any(key[:2] == (provider, place) for key in table):
            table[(provider, place, model)] = Frequency(provider, model, 0, 0, [], locale=place)
    order = list(slots)
    return sorted(table.values(), key=lambda f: order.index((f.provider, f.locale)))


def _where(text: str, names: list[str], found) -> list[int] | None:
    """The passage that ranks the product (the extraction's quote), else its first name."""
    if found.evidence:
        at = span(text, found.evidence)
        if at:
            return at
    match = mention.pattern(names).search(text)
    return [match.start(), match.end()] if match else None


def summary(round_: Round, products: list[list[str]] | None = None) -> dict:
    """The round as `round.json` holds it: everything but the raw responses."""
    data = {
        "schema": schema("round"),
        "question": round_.question,
        "asked_at": round_.asked_at.astimezone(UTC).isoformat(),
        "search": round_.search,
        "runs": round_.runs,
        "brand": round_.brand,
        "set": round_.set or None,
        "purpose": round_.purpose or None,
        "locales": [_locale(place) for place in round_.locales],
        "answered": len(round_.results) - len(failures(round_)),
        "failed": len(failures(round_)),
        "cost": cost(round_),
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
                        "in": [
                            {"answer": a, "range": rng}
                            for a, rng in zip(f.answers, f.ranges, strict=True)
                        ],
                    }
                    for f in frequency(round_, names)
                ],
                "claims": [
                    {
                        "attribute": c.attribute,
                        "value": c.value,
                        "answers": c.answers,
                        "providers": c.providers,
                        "quote": c.quote,
                        "unverified": c.unverified,
                        "in": c.found_in,
                    }
                    for c in product_claims(round_, names)
                ],
                "links": link_checks(round_, names[0]),
                "gaps": fact_gaps(round_, names[0]),
                "places": citations.places(names),
                "cited": [
                    {
                        "provider": c.provider,
                        "answers": c.answers,
                        "citing": c.citing,
                        "kinds": c.kinds,
                        "pages": c.pages,
                    }
                    for c in citations.product_citations(round_, names)
                ],
            }
            for names in products
        ]
    found = rivals(round_, products)
    data["third_party"] = citations.third_party(
        round_, products or [], [rival.name for rival in found.rivals]
    )
    data["rivals"] = {
        "read": found.read,
        "missing": found.missing or None,
        "products": [
            {
                "name": rival.name,
                "answers": rival.answers,
                "ranks": rival.ranks,
                "providers": rival.providers,
                "reason": rival.reason,
                "exists": exists(round_, rival.name),
            }
            for rival in found.rivals
        ],
    }
    return data


def cost(round_: Round) -> dict:
    """The estimate made before the round and the actual cost per provider, in USD; an
    actual of null is a model the price table does not know."""
    spent = round_.spent if round_.spent is not None else costs.actual(round_)
    known = [v for v in spent.values() if v is not None]
    return {
        "estimate": round_.estimate,
        "actual": spent,
        "total": round(sum(known), 6) if known else None,
        "prices_as_of": costs.PRICES_AS_OF,
    }


def fact_gaps(round_: Round, product: str) -> list[dict] | None:
    """The product's fact gaps, or None where no product file was compared."""
    gaps = round_.gaps.get(product)
    return None if gaps is None else [dict(g.__dict__) for g in gaps]


def link_checks(round_: Round, product: str) -> list[dict] | None:
    """The product's attributed links as followed, or None where --check-links did not run."""
    checks = round_.links.get(product)
    if checks is None:
        return None
    return [
        {
            "provider": c.provider,
            "run": c.run,
            "url": c.url,
            "status": c.status,
            "final_url": c.final_url,
            "title": c.title,
            "verdict": c.verdict,
        }
        for c in checks
    ]


def exists(round_: Round, name: str) -> dict | None:
    """The lookup's verdict on a rival, or None where none was looked up."""
    verdict = round_.checks.get(key(name))
    if verdict is None:
        return None
    return {
        "status": verdict.status,
        "url": verdict.url,
        "evidence": verdict.evidence,
        "via": verdict.via,
    }


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
            "claims": None,
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
        "claims": (
            None
            if answer.claims is None
            else [
                {
                    "product": c.product,
                    "attribute": c.attribute,
                    "value": c.value,
                    "quote": c.quote,
                    "verified": c.verified,
                }
                for c in answer.claims
            ]
        ),
        "extracted_by": answer.extracted_by or None,
        "extraction_error": answer.extraction_error,
        "error": None,
    }


def slug(text: str, limit: int = 40) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return words[:limit].rstrip("-") or "question"


def save_round(
    round_: Round,
    out: Path,
    products: list[list[str]] | None = None,
    directory: Path | None = None,
) -> Path:
    """Write the round under `out`, or into `directory` when given (a set's question)."""
    if directory is None:
        stamp = round_.asked_at.astimezone(UTC)
        name = f"{stamp.strftime('%H%M%S')}-{slug(round_.question)}"
        directory = _fresh(out / stamp.strftime("%Y-%m-%d") / name)
    directory.mkdir(parents=True, exist_ok=True)
    _write(directory / "round.json", summary(round_, products))
    for r in round_.results:
        if r.answer is not None:
            _write(directory / raw_name(r), r.answer.raw)
    try:
        source = (directory / "round.json").relative_to(out).as_posix()
    except ValueError:
        source = (directory / "round.json").as_posix()
    series.append(out, series.rows(round_, products or [], source))
    return directory


def _fresh(directory: Path) -> Path:
    """The directory, or `<name>-2`, `-3`... when a round of the same question in the
    same second is already there: a round never overwrites another."""
    candidate, n = directory, 1
    while (candidate / "round.json").exists():
        n += 1
        candidate = directory.with_name(f"{directory.name}-{n}")
    return candidate


def raw_name(r: Result) -> str:
    """`<provider>-<run>.json`, or `<provider>-<COUNTRY>-<run>.json` in a locale."""
    place = f"-{r.locale.country}" if r.locale else ""
    return f"{r.provider}{place}-{r.run}.json"


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
