"""`askround export`: a product's numbers from the series, for another project's data.

A project that keeps daily numbers per product (a dashboard) should take askround's
without a copy by hand. The export reads the series (series.py) and writes one row per
day, provider and question:

    day, product, provider, question, purpose, locale, answers, named, frequency,
    best_position, mean_position, rivals, cited_pages

`rivals` counts the other products the answers recommended (where the extraction pass
ran; empty otherwise), `cited_pages` the product's own pages the answers cited.

As CSV or JSON rows, or as `daily`: the shape a daily.json of numbers per product and
day takes, `{product: {day: {"assistants": {...}}}}`, summed over questions, with
the providers apart - ready to merge into such a file.

Brand questions (which name the product on purpose) are left out, as everywhere.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict

FIELDS = (
    "day",
    "product",
    "provider",
    "question",
    "purpose",
    "locale",
    "answers",
    "named",
    "frequency",
    "best_position",
    "mean_position",
    "rivals",
    "cited_pages",
)


def rows(series: list[dict], product: str, since: str = "", until: str = "") -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in series:
        if row["error"] or row.get("brand") or product not in row["products"]:
            continue
        if (since and row["day"] < since) or (until and row["day"] > until):
            continue
        key = (row["day"], row["provider"], row["question"], row.get("purpose"), row["locale"])
        groups[key].append(row)
    out = []
    for (day, provider, question, purpose, locale), items in sorted(groups.items()):
        seen = [i["products"][product] for i in items]
        positions = [s["position"] for s in seen if s["position"] is not None]
        named = sum(bool(s["named"]) for s in seen)
        rivals = {
            name
            for i in items
            for name in i["recommendations"] or []
            if name.lower() != product.lower()
        }
        extracted = any(i["recommendations"] is not None for i in items)
        out.append(
            {
                "day": day,
                "product": product,
                "provider": provider,
                "question": question,
                "purpose": purpose or "",
                "locale": locale or "",
                "answers": len(items),
                "named": named,
                "frequency": round(named / len(items), 4),
                "best_position": min(positions) if positions else None,
                "mean_position": round(sum(positions) / len(positions), 2) if positions else None,
                "rivals": len(rivals) if extracted else None,
                "cited_pages": len({p for s in seen for p in s.get("cited") or []}),
            }
        )
    return out


def to_csv(items: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for item in items:
        writer.writerow({k: "" if item[k] is None else item[k] for k in FIELDS})
    return buffer.getvalue()


def daily(items: list[dict], key: str) -> dict:
    """{key: {day: {"assistants": {answers, named, frequency, best_position, providers}}}}"""
    days: dict[str, dict] = {}
    for item in items:
        day = days.setdefault(
            item["day"],
            {"answers": 0, "named": 0, "best_position": None, "providers": {}},
        )
        day["answers"] += item["answers"]
        day["named"] += item["named"]
        if item["best_position"] is not None:
            best = day["best_position"]
            day["best_position"] = (
                min(best, item["best_position"]) if best else item["best_position"]
            )
        p = day["providers"].setdefault(item["provider"], {"answers": 0, "named": 0})
        p["answers"] += item["answers"]
        p["named"] += item["named"]
    for day in days.values():
        day["frequency"] = round(day["named"] / day["answers"], 4) if day["answers"] else 0.0
    return {key: {d: {"assistants": days[d]} for d in sorted(days)}}
