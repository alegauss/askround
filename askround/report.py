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

from askround import citations, mention
from askround.claims import product_claims
from askround.extract import Claim, Recommendation
from askround.gaps import Gap
from askround.links import LinkCheck
from askround.lookup import Verdict
from askround.provenance import answer_id, schema
from askround.providers import Answer, Locale, Source
from askround.rivals import key, rivals
from askround.round import (
    Result,
    Round,
    cost,
    exists,
    fact_gaps,
    failures,
    frequency,
    link_checks,
)

RIVALS_SHOWN = 10


def find_round(path: Path | None, out: Path) -> Path:
    """The round.json or set.json a path names: the file, a round's or a set's
    directory, or with no path the latest round or set under `out`."""
    if path is None:
        found = sorted(
            [*out.glob("*/*/round.json"), *out.glob("*/*/set.json")],
            key=lambda p: (p.parent.parent.name, p.parent.name),
        )
        if not found:
            raise FileNotFoundError(f"no round under {out}")
        return found[-1]
    if path.is_dir():
        path = path / "set.json" if (path / "set.json").is_file() else path / "round.json"
    if not path.is_file():
        raise FileNotFoundError(f"no round.json at {path}")
    return path


def build_set(path: Path) -> dict:
    """A prompt set run as data: its index, and each question's report."""
    index = json.loads(path.read_text(encoding="utf-8"))
    questions = []
    for q in index["questions"]:
        round_path = path.parent / q["round"]
        round_, products = load_round(round_path)
        questions.append(
            {**q, "report": build(round_, products or [index["names"]], str(round_path))}
        )
    return {
        "schema": schema("set"),
        "set": str(path),
        "product": index["product"],
        "asked_at": index["asked_at"],
        "questions": questions,
    }


def set_brief(path: Path) -> dict:
    """A prompt set run as briefs: each question's few hundred tokens, not its report."""
    index = json.loads(path.read_text(encoding="utf-8"))
    questions = []
    for q in index["questions"]:
        round_path = path.parent / q["round"]
        round_, products = load_round(round_path)
        found = brief(round_, products or [index["names"]], str(round_path.parent))
        found.pop("schema", None)
        questions.append({"n": q["n"], "purpose": q["purpose"], "locale": q["locale"], **found})
    return {
        "schema": schema("set-brief"),
        "set": str(path.parent),
        "product": index["product"],
        "questions": questions,
    }


def set_markdown(report: dict) -> str:
    product = report["product"]
    providers: list[str] = []
    for q in report["questions"]:
        for row in _rows(q["report"], product):
            if row["provider"] not in providers:
                providers.append(row["provider"])
    lines = [
        f"# {_cell(product)}: prompt set",
        "",
        f"asked {report['asked_at'][:16].replace('T', ' ')} UTC, {len(report['questions'])} "
        "questions. API answers, not the chat apps.",
        "",
    ]
    neutral = [q for q in report["questions"] if not q.get("brand")]
    brand = [q for q in report["questions"] if q.get("brand")]
    lines += _set_table(neutral, product, providers)
    lines += ["", "Each cell: runs naming it, then its position in each run.", ""]
    if brand:
        lines += [
            "Brand questions name the product on purpose, so they show what is said about it,",
            "not whether it is found; they are kept out of the table above.",
            "",
            *_set_table(brand, product, providers),
            "",
        ]
    for q in report["questions"]:
        body = markdown(q["report"])
        demoted = "\n".join(
            "#" + line if line.startswith("#") else line for line in body.splitlines()
        )
        lines += [
            demoted.replace(f"# {_cell(q['text'])}", f"# {q['n']}. {_cell(q['text'])}", 1),
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def _set_table(questions: list[dict], product: str, providers: list[str]) -> list[str]:
    lines = [
        "| # | question | purpose | " + " | ".join(providers) + " |",
        "|---|---|---|" + "---|" * len(providers),
    ]
    for q in questions:
        cells = {}
        for row in _rows(q["report"], product):
            cells[row["provider"]] = f"{row['named']}/{row['runs']} {_positions(row)}"
        question = _cell(q["text"]) + (f" ({q['locale']})" if q["locale"] else "")
        shown = " | ".join(cells.get(p, "-") for p in providers)
        lines.append(f"| {q['n']} | {question} | {_cell(q['purpose']) or '-'} | {shown} |")
    return lines


def _rows(report: dict, product: str) -> list[dict]:
    for p in report["products"]:
        if p["product"] == product:
            return p["frequency"]
    return []


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
    round_ = Round(
        data["question"],
        datetime.fromisoformat(data["asked_at"]),
        [_result(item) for item in data["results"]],
        search=data.get("search", True),
        runs=data.get("runs", 1),
        locales=[_locale(x) for x in data.get("locales") or []],
        brand=bool(data.get("brand", False)),
        set=data.get("set") or "",
        purpose=data.get("purpose") or "",
        estimate=(data.get("cost") or {}).get("estimate"),
        spent=(data.get("cost") or {}).get("actual") or {},
    )
    _restore_checks(round_, data)
    products = [p["names"] for p in data.get("products") or []]
    return round_, products


def _result(item: dict) -> Result:
    """One answer of a round.json; a field an older askround did not write yet takes the
    value it had then (one run, no locale)."""
    locale = _locale(item.get("locale"))
    run = item.get("run", 1)
    if item.get("error"):
        return Result(item["provider"], item["model"], run, error=item["error"], locale=locale)
    return Result(item["provider"], item["model"], run, answer=_answer(item), locale=locale)


def _restore_checks(round_: Round, data: dict) -> None:
    """What the passes after the round found: rival lookups, links followed, fact gaps."""
    for rival in (data.get("rivals") or {}).get("products") or []:
        verdict = rival.get("exists")
        if verdict:
            round_.checks[key(rival["name"])] = Verdict(rival["name"], **verdict)
    for product in data.get("products") or []:
        if product.get("links") is not None:
            round_.links[product["product"]] = [LinkCheck(**c) for c in product["links"]]
        if product.get("gaps") is not None:
            round_.gaps[product["product"]] = [Gap(**g) for g in product["gaps"]]


TOP = 5


def brief(round_: Round, products: list[list[str]], source: str = "") -> dict:
    """The round in a few hundred tokens (law L1): what was found, each fact with the
    ids of the answers it came from; the text stays behind askround_answer."""
    answered = [r for r in round_.results if r.answer is not None]
    out: dict = {
        "schema": schema("brief"),
        "q": round_.question,
        "round": source,
        "answers": len(answered),
        "failed": [answer_id(r) for r in failures(round_)],
        "cost": cost(round_)["total"],
        "products": [_brief_product(round_, answered, names) for names in products],
    }
    found = rivals(round_, products)
    if found.read:
        out["rivals"] = [
            {"name": v.name, "n": f"{v.answers}/{found.read}", "best": v.best}
            for v in found.rivals[:TOP]
        ]
    return out


def _brief_product(round_: Round, answered: list, names: list[str]) -> dict:
    by_provider: dict[str, dict] = {}
    naming: list[str] = []
    for r in answered:
        seen = mention.locate(r.answer, names)
        row = by_provider.setdefault(r.provider, {"named": 0, "of": 0, "best": None})
        row["of"] += 1
        if seen.named:
            row["named"] += 1
            naming.append(answer_id(r))
        if seen.position is not None:
            row["best"] = seen.position if row["best"] is None else min(row["best"], seen.position)
    ranked = _brief_claims(answered, names)
    product: dict = {
        "name": names[0],
        "named": {
            p: f"{v['named']}/{v['of']}" + (f" #{v['best']}" if v["best"] else "")
            for p, v in by_provider.items()
        },
        "in": naming,
    }
    if ranked:
        product["claims"] = [{"c": text, "in": ids} for text, ids in ranked]
    gaps = round_.gaps.get(names[0])
    if gaps:
        product["gaps"] = [f"{g.attribute}: {g.value} ({g.verdict} '{g.fact}')" for g in gaps[:TOP]]
    return product


def _brief_claims(answered: list, names: list[str]) -> list[tuple[str, list[str]]]:
    """The product's verified claims, most made first, each with its answers' ids."""
    target = mention.pattern(names)
    claims: dict[str, list[str]] = {}
    for r in answered:
        for c in r.answer.claims or []:
            if c.verified and target.search(c.product):
                claims.setdefault(f"{c.attribute}: {c.value}", []).append(answer_id(r))
    return sorted(claims.items(), key=lambda kv: -len(kv[1]))[:TOP]


def build(round_: Round, products: list[list[str]], source: str = "") -> dict:
    """The report as data: the same facts the Markdown shows."""
    found = rivals(round_, products)
    return {
        "schema": schema("report"),
        "round": source,
        "question": round_.question,
        "asked_at": round_.asked_at.isoformat(),
        "search": round_.search,
        "runs": round_.runs,
        "brand": round_.brand,
        "cost": cost(round_),
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
                {
                    "name": v.name,
                    "answers": v.answers,
                    "ranks": v.ranks,
                    "providers": v.providers,
                    "exists": exists(round_, v.name),
                }
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
        "links": link_checks(round_, names[0]),
        "gaps": fact_gaps(round_, names[0]),
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
    if report.get("brand"):
        facts.append("a brand question: it names the product on purpose")
    if report["locales"]:
        facts.append("locales " + ", ".join(report["locales"]))
    if not report["search"]:
        facts.append("web search off")
    facts.append(f"{report['answered']} answers")
    if report["failed"]:
        facts.append(f"{len(report['failed'])} failed")
    spent = (report.get("cost") or {}).get("total")
    if spent is not None:
        facts.append(f"cost ${spent:.4f}")
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
    lines += _gaps_markdown(product["gaps"])
    lines += _links_markdown(product["links"])
    return lines


def _gaps_markdown(gaps: list[dict] | None) -> list[str]:
    if gaps is None:
        return []
    if not gaps:
        return ["Fact gaps: none. Every claim compared agrees with the product file.", ""]
    lines = [
        "**Fact gaps** - what the answers get wrong or leave in doubt:",
        "",
        "| claim | providers | verdict | the fact | say it plainly on |",
        "|---|---|---|---|---|",
    ]
    for g in gaps:
        by = ", ".join(f"{p} {n}" for p, n in g["providers"].items())
        claim = f"{_cell(g['attribute'])}: {_cell(g['value'])}"
        lines.append(
            f"| {claim} | {by} | {g['verdict']} | {_cell(g['fact'])} | {_cell(g['page']) or '-'} |"
        )
    cited = sorted({page for g in gaps for page in g["cited"]})
    lines.append("")
    lines.append("The answers cited of its pages: " + (", ".join(cited) if cited else "none") + ".")
    lines.append("")
    return lines


def _links_markdown(links: list[dict] | None) -> list[str]:
    if links is None:
        return []
    wrong = [c for c in links if c["verdict"] != "ok"]
    lines = [f"Links given for it: {len(links)} followed, {len(wrong)} not its own.", ""]
    if wrong:
        lines += ["| provider | run | link | lands on | verdict |", "|---|---|---|---|---|"]
        for c in wrong:
            lands = _cell(c["title"] or c["final_url"]) if c["status"] else "unreachable"
            row = f"| {c['provider']} | {c['run']} | {_cell(c['url'])} | {lands} | {c['verdict']} |"
            lines.append(row)
        lines.append("")
    return lines


def _rivals_markdown(found: dict) -> list[str]:
    if not found["top"]:
        return [f"_{found['missing']}_", ""] if found["missing"] else []
    lines = [
        f"## Rivals (in {found['read']} answers read)",
        "",
        "| product | answers | ranks | providers | exists |",
        "|---|---|---|---|---|",
    ]
    for v in found["top"]:
        ranks = ", ".join(f"#{r}" for r in v["ranks"])
        by = ", ".join(f"{p} {n}" for p, n in v["providers"].items())
        share = f"{v['answers']}/{found['read']}"
        lines.append(f"| {_cell(v['name'])} | {share} | {ranks} | {by} | {_exists(v['exists'])} |")
    if found["more"]:
        lines.append(f"\n{found['more']} more in round.json.")
    flagged = [v["name"] for v in found["top"] if (v["exists"] or {}).get("status") == "not_found"]
    if flagged:
        lines.append(
            f"\n**Not found anywhere:** {', '.join(flagged)}. The answers may have invented them."
        )
    lines.append("")
    return lines


def _exists(verdict: dict | None) -> str:
    if verdict is None:
        return "not checked"
    status = verdict["status"].replace("_", " ")
    return f"[{status}]({verdict['url']})" if verdict["url"] else status
