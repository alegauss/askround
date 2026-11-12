"""`askround report`: a stored round, read back and summed up in one short report.

The report is what a person deciding needs, without opening any answer: for each
product, one table of provider (and locale) with the share of runs naming it and its
positions, then what the answers claim about it, which of its pages they cite, and the
rivals around it. It is printed as Markdown for a person or as JSON for a pipeline;
the JSON carries the same facts and never the answers' text (law L1: context is cost -
the text stays in round.json and the raw responses next to it).

A round is read from its `round.json`, so a report can be made again at any time,
for other products than the ones the round was asked about.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from askround import citations
from askround.claims import product_claims
from askround.extract import Claim, Recommendation
from askround.providers import Answer, Locale, Source
from askround.rivals import rivals
from askround.round import Result, Round, failures, frequency

RIVALS_SHOWN = 10


def find_round(path: Path | None, out: Path) -> Path:
    """The round.json a path names: the file, a round's directory, or with no path the
    latest round under `out`."""
    if path is None:
        found = sorted(out.glob("*/*/round.json"))
        if not found:
            raise FileNotFoundError(f"no round under {out}")
        return found[-1]
    if path.is_dir():
        path = path / "round.json"
    if not path.is_file():
        raise FileNotFoundError(f"no round.json at {path}")
    return path


def _locale(data: dict | None) -> Locale | None:
    return Locale(data["country"], data.get("language")) if data else None


def _answer(item: dict) -> Answer:
    recs = item.get("recommendations")
    claims = item.get("claims")
    answered = item.get("answered_at")
    return Answer(
        item["provider"],
        item["model"],
        item.get("text") or "",
        {},
        search=bool(item.get("search", True)),
        sources=[Source(s["url"], s.get("title", "")) for s in item.get("sources") or []],
        queries=list(item.get("queries") or []),
        served_model=item.get("served_model") or "",
        settings=item.get("settings") or {},
        answered_at=datetime.fromisoformat(answered) if answered else None,
        locale=_locale(item.get("locale")),
        locale_ignored=list((item.get("locale") or {}).get("ignored") or []),
        recommendations=None if recs is None else [Recommendation(**r) for r in recs],
        claims=None if claims is None else [Claim(**c) for c in claims],
        extracted_by=item.get("extracted_by") or "",
        extraction_error=item.get("extraction_error"),
    )


def load_round(path: Path) -> tuple[Round, list[list[str]]]:
    """The round a round.json holds, and the products it was asked about."""
    data = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for item in data["results"]:
        locale = _locale(item.get("locale"))
        if item.get("error"):
            results.append(
                Result(
                    item["provider"], item["model"], item["run"], error=item["error"], locale=locale
                )
            )
        else:
            results.append(
                Result(
                    item["provider"],
                    item["model"],
                    item["run"],
                    answer=_answer(item),
                    locale=locale,
                )
            )
    round_ = Round(
        data["question"],
        datetime.fromisoformat(data["asked_at"]),
        results,
        search=data.get("search", True),
        runs=data.get("runs", 1),
        locales=[_locale(x) for x in data.get("locales") or []],
    )
    products = [p["names"] for p in data.get("products") or []]
    return round_, products


def build(round_: Round, products: list[list[str]], source: str = "") -> dict:
    """The report as data: the same facts the Markdown shows."""
    found = rivals(round_, products)
    return {
        "round": source,
        "question": round_.question,
        "asked_at": round_.asked_at.isoformat(),
        "search": round_.search,
        "runs": round_.runs,
        "locales": [str(x) for x in round_.locales],
        "answered": len(round_.results) - len(failures(round_)),
        "failed": [
            {
                "provider": r.provider,
                "run": r.run,
                "locale": str(r.locale) if r.locale else None,
                "error": r.error,
            }
            for r in failures(round_)
        ],
        "extracted": any(r.answer and r.answer.recommendations is not None for r in round_.results),
        "products": [_product(round_, names) for names in products],
        "rivals": {
            "read": found.read,
            "missing": found.missing or None,
            "top": [
                {"name": v.name, "answers": v.answers, "ranks": v.ranks, "providers": v.providers}
                for v in found.rivals[:RIVALS_SHOWN]
            ],
            "more": max(0, len(found.rivals) - RIVALS_SHOWN),
        },
    }


def _product(round_: Round, names: list[str]) -> dict:
    return {
        "product": names[0],
        "names": names,
        "frequency": [
            {
                "provider": f.provider,
                "locale": str(f.locale) if f.locale else None,
                "model": f.model,
                "runs": f.runs,
                "named": f.named,
                "positions": f.positions,
                "ranked_by": f.ranked_by,
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
            }
            for c in product_claims(round_, names)
            if c.answers
        ],
        "cited": [
            {
                "provider": c.provider,
                "answers": c.answers,
                "citing": c.citing,
                "kinds": c.kinds,
                "pages": c.pages,
            }
            for c in citations.product_citations(round_, names)
        ]
        if citations.places(names)
        else None,
    }


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _positions(row: dict) -> str:
    marks = ["*" if by == "extraction" else "" for by in row["ranked_by"]]
    shown = ["-" if p is None else f"#{p}{m}" for p, m in zip(row["positions"], marks, strict=True)]
    return ", ".join(shown) or "-"


def markdown(report: dict) -> str:
    lines = [f"# {_cell(report['question'])}", ""]
    facts = [
        f"asked {report['asked_at'][:16].replace('T', ' ')} UTC",
        f"{report['runs']} run(s) per provider",
    ]
    if report["locales"]:
        facts.append("locales " + ", ".join(report["locales"]))
    if not report["search"]:
        facts.append("web search off")
    facts.append(f"{report['answered']} answers")
    if report["failed"]:
        facts.append(f"{len(report['failed'])} failed")
    lines += [", ".join(facts) + ". API answers, not the chat apps.", ""]
    for product in report["products"]:
        lines += _product_markdown(product, report)
    lines += _rivals_markdown(report["rivals"])
    if report["failed"]:
        lines += ["## Failed", ""]
        for f in report["failed"]:
            where = f" {f['locale']}" if f["locale"] else ""
            lines.append(f"- {f['provider']}{where} run {f['run']}: {_cell(f['error'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _product_markdown(product: dict, report: dict) -> list[str]:
    lines = [f"## {product['product']}", ""]
    with_locale = bool(report["locales"])
    head = "| provider |" + (" locale |" if with_locale else "") + " named in | positions | model |"
    lines += [head, "|" + "---|" * (head.count("|") - 1)]
    for row in product["frequency"]:
        locale = f" {row['locale']} |" if with_locale else ""
        share = f"{row['named']}/{row['runs']}"
        lines.append(
            f"| {row['provider']} |{locale} {share} | {_positions(row)} | {row['model']} |"
        )
    if any("extraction" in row["ranked_by"] for row in product["frequency"]):
        lines.append("")
        lines.append("\\* ranked by the extraction pass")
    lines.append("")
    if product["claims"]:
        lines += ["What the answers claim:", "", "| claim | providers | passage |", "|---|---|---|"]
        for c in product["claims"]:
            by = ", ".join(f"{p} {n}" for p, n in c["providers"].items())
            lines.append(
                f"| {_cell(c['attribute'])}: {_cell(c['value'])} | {by} | {_cell(c['quote'])} |"
            )
        lines.append("")
    if product["cited"] is not None:
        lines += [
            "Its pages cited:",
            "",
            "| provider | answers citing | kinds | pages |",
            "|---|---|---|---|",
        ]
        for c in product["cited"]:
            kinds = ", ".join(f"{k} {n}" for k, n in sorted(c["kinds"].items())) or "-"
            pages = "<br>".join(f"{n}x {url}" for url, n in c["pages"].items()) or "-"
            lines.append(f"| {c['provider']} | {c['citing']}/{c['answers']} | {kinds} | {pages} |")
        lines.append("")
    return lines


def _rivals_markdown(found: dict) -> list[str]:
    if not found["top"]:
        return [f"_{found['missing']}_", ""] if found["missing"] else []
    lines = [
        f"## Rivals (in {found['read']} answers read)",
        "",
        "| product | answers | ranks | providers |",
        "|---|---|---|---|",
    ]
    for v in found["top"]:
        ranks = ", ".join(f"#{r}" for r in v["ranks"])
        by = ", ".join(f"{p} {n}" for p, n in v["providers"].items())
        lines.append(f"| {_cell(v['name'])} | {v['answers']}/{found['read']} | {ranks} | {by} |")
    if found["more"]:
        lines.append(f"\n{found['more']} more in round.json.")
    lines.append("")
    return lines
