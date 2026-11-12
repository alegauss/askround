"""A prompt set run: every question of a product file, asked the same way each time.

`askround run modelado.toml` asks each `[[question]]` as its own round (its runs and
locale as the file sets them), all about the product the file describes, and keeps
them together as one run:

    <out>/<YYYY-MM-DD>/<HHMMSS>-set-<product>/
        set.json                 the product, when, and each question with its round
        01-<question>/round.json one ordinary round per question, raw answers beside it
        02-<question>/round.json

Each question's directory is an ordinary round, so `askround report` reads any one of
them; given the set's directory it reports the whole run, beginning with one table of
question by provider.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from askround import costs, gaps, leading, links, private
from askround.extract import extract_round
from askround.product import Product
from askround.round import DEFAULT_RUNS, Round, run_round, save_round, slug


def check(product: Product) -> None:
    """Refuse the whole set, before any call, if a question carries personal data or,
    unmarked as a brand question, names the product."""
    for n, question in enumerate(product.questions, start=1):
        found = private.scan(question.text)
        if found:
            raise ValueError(private.refusal(f"question {n}", question.text, found))
        hits = leading.leads(question.text, product.names, product.phrases)
        if hits and not question.brand:
            raise ValueError(f"question {n}: {leading.refusal(question.text, hits)}")


def estimate(product: Product, providers: list, runs: int | None, search: bool, extractor=None):
    """What the whole set should cost: each question's calls, summed."""
    calls = sum(runs or q.runs or DEFAULT_RUNS for q in product.questions)
    return costs.estimate(providers, calls, search, extractor)


def set_directory(product: Product, out: Path, now: datetime) -> Path:
    stamp = now.astimezone(UTC)
    name = f"{stamp.strftime('%H%M%S')}-set-{slug(product.name)}"
    return out / stamp.strftime("%Y-%m-%d") / name


def run_set(
    product: Product,
    providers: list,
    out: Path,
    *,
    search: bool = True,
    runs: int | None = None,
    extractor=None,
    get=None,
    now: datetime | None = None,
    source: str = "",
) -> tuple[Path, list[Round]]:
    """Ask every question of the product file; `runs` overrides each question's own."""
    if not product.questions:
        raise ValueError(f"{product.name}: the product file has no [[question]]")
    check(product)
    started = now or datetime.now(UTC)
    directory = set_directory(product, out, started)
    rounds: list[Round] = []
    index = []
    for n, question in enumerate(product.questions, start=1):
        round_ = run_round(
            question.text,
            providers,
            search=search,
            runs=runs or question.runs or DEFAULT_RUNS,
            locales=[question.locale] if question.locale else None,
        )
        round_.brand = question.brand
        round_.set = product.name
        round_.purpose = question.purpose
        round_.estimate = costs.as_dict(
            costs.estimate(providers, round_.runs * max(1, len(round_.locales)), search, extractor)
        )
        if extractor is not None:
            before = extractor.spent
            extract_round(round_, extractor)
            if product.facts:
                round_.gaps[product.name] = gaps.compare(round_, product, extractor)
            round_.extraction_cost = extractor.spent - before
        if get is not None:
            round_.links[product.name] = links.check_links(round_, product.names, get=get)
        where = directory / f"{n:02d}-{slug(question.text, 30)}"
        save_round(round_, out, [product.names], directory=where)
        rounds.append(round_)
        index.append(
            {
                "n": n,
                "text": question.text,
                "purpose": question.purpose,
                "locale": str(question.locale) if question.locale else None,
                "runs": round_.runs,
                "brand": question.brand,
                "round": f"{where.name}/round.json",
            }
        )
    summary = {
        "product": product.name,
        "names": product.names,
        "file": source,
        "asked_at": started.isoformat(),
        "search": search,
        "questions": index,
    }
    (directory / "set.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return directory, rounds
