"""The series: every answer of every round, kept in order, so change shows over time.

One round is a snapshot. Whether a product stays first after its page changes, or a
rival overtakes it, is a question about time, so every saved round appends one row per
answer to `<out>/series.jsonl` (JSON Lines: append-only, readable and diffable, no
database). A row holds what the answer was and what was read from it:

    asked_at, day, week (ISO, "2026-W46"), month, set, question, purpose, brand,
    provider, model (the one that answered), locale, run, round (its round.json),
    products: {name: {named, position, cited}} for each product the round tracked
              (cited: its own pages the answer cited),
    recommendations (names, in order), cited (normalised pages), claims, error

The rounds stay the evidence: `rebuild` reads every round.json under `out` and writes
the series again from them, so the series is an index that can always be recomputed.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from askround import citations, mention

FILE = "series.jsonl"
PERIODS = ("day", "week", "month")


def _periods(moment: datetime) -> dict[str, str]:
    year, week, _ = moment.isocalendar()
    return {
        "day": moment.strftime("%Y-%m-%d"),
        "week": f"{year}-W{week:02d}",
        "month": moment.strftime("%Y-%m"),
    }


def rows(round_, products: list[list[str]], source: str = "") -> list[dict]:
    """One row per answer (or failure) of the round."""
    out = []
    for r in round_.results:
        answer = r.answer
        moment = answer.answered_at if answer and answer.answered_at else round_.asked_at
        row = {
            "asked_at": round_.asked_at.isoformat(),
            **_periods(moment),
            "set": round_.set,
            "question": round_.question,
            "purpose": round_.purpose,
            "brand": round_.brand,
            "provider": r.provider,
            "model": (answer.served_model or answer.model) if answer else r.model,
            "locale": str(r.locale) if r.locale else None,
            "run": r.run,
            "round": source,
            "error": r.error,
            "products": {},
            "recommendations": None,
            "cited": [],
            "claims": None,
        }
        if answer is not None:
            pages = citations.cited(answer)
            for names in products:
                found = mention.locate(answer, names)
                places = citations.places(names)
                own = [p.url for p in pages if any(citations.owns(x, p) for x in places)]
                row["products"][names[0]] = {
                    "named": found.named,
                    "position": found.position,
                    "cited": own,
                }
            if answer.recommendations is not None:
                standing = mention.standing(answer.text, answer.recommendations)
                row["recommendations"] = [mention.core(rec.name) for rec in standing]
            row["cited"] = [page.url for page in citations.cited(answer)]
            if answer.claims is not None:
                row["claims"] = [
                    {"product": c.product, "attribute": c.attribute, "value": c.value}
                    for c in answer.claims
                    if c.verified
                ]
        out.append(row)
    return out


def append(out: Path, new: list[dict]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / FILE).open("a", encoding="utf-8") as handle:
        for row in new:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load(out: Path) -> list[dict]:
    path = out / FILE
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def rebuild(out: Path, skipped: list[str] | None = None) -> int:
    """Write the series again from every round.json under `out`; the rows written. A
    file that cannot be read is named in `skipped`, never silently dropped."""
    from askround.report import load_round  # the report reads rounds back

    written: list[dict] = []
    for path in sorted(out.rglob("round.json")):
        try:
            round_, products = load_round(path)
        except (KeyError, TypeError, ValueError) as error:
            if skipped is not None:
                skipped.append(f"{path}: {type(error).__name__}: {error}")
            continue
        written += rows(round_, products, path.relative_to(out).as_posix())
    written.sort(key=lambda row: row["asked_at"])
    (out / FILE).write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in written), encoding="utf-8"
    )
    return len(written)


def frequency(
    series: list[dict], product: str, by: str = "week", question: str | None = None
) -> dict[str, dict[str, dict[str, int]]]:
    """{period: {provider: {"named": n, "answers": n}}} for the rows that tracked the
    product (brand questions left out), oldest period first."""
    if by not in PERIODS:
        raise ValueError(f"by must be one of {', '.join(PERIODS)}")
    table: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"named": 0, "answers": 0})
    )
    for row in series:
        if row["error"] or row.get("brand") or product not in row["products"]:
            continue
        if question and question.lower() not in row["question"].lower():
            continue
        cell = table[row[by]][row["provider"]]
        cell["answers"] += 1
        cell["named"] += bool(row["products"][product]["named"])
    return {period: dict(table[period]) for period in sorted(table)}
