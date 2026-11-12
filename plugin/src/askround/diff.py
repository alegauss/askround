"""`askround diff`: what changed between two rounds of the same questions.

A weekly review does not want the whole report again; it wants what moved: a rival
that appeared, a rank lost on one provider, a page no longer cited, a claim that became
right after the product's page changed. Two rounds of one question, or two runs of one
prompt set (matched question by question), are compared per question and provider:

- share: the runs naming the product, and its best position;
- rivals: products recommended now and not before, and the other way round;
- cited: the product's pages cited now and not before, and the other way round;
- claims: what the answers claim about it now and not before, and the other way round.

Rivals and claims need the extraction pass on both sides; where either side lacks it
the comparison says so instead of reporting everything as new.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from askround import citations
from askround.claims import product_claims
from askround.report import load_round
from askround.rivals import rivals
from askround.round import Round, frequency


@dataclass(frozen=True)
class Change:
    question: str
    provider: str
    kind: str  # share, rival, cited or claims
    detail: str


@dataclass
class Snapshot:
    named: int
    answers: int
    best: int | None
    rivals: set[str] | None
    cited: set[str]
    claims: set[str] | None


def units(path: Path) -> tuple[dict[str, tuple[Round, list[list[str]]]], str]:
    """The rounds a round.json or set.json holds, by question; and the set's product."""
    if path.name == "set.json":
        index = json.loads(path.read_text(encoding="utf-8"))
        found = {}
        for q in index["questions"]:
            round_, products = load_round(path.parent / q["round"])
            found[q["text"]] = (round_, products or [index["names"]])
        return found, index["product"]
    round_, products = load_round(path)
    return {round_.question: (round_, products)}, ""


def snapshot(round_: Round, names: list[str], provider: str) -> Snapshot:
    rows = [f for f in frequency(round_, names) if f.provider == provider]
    positions = [p for f in rows for p in f.positions if p is not None]
    extracted = any(
        r.answer is not None and r.answer.recommendations is not None
        for r in round_.results
        if r.provider == provider
    )
    found = rivals(round_, [names])
    pages = {
        page
        for c in citations.product_citations(round_, names)
        if c.provider == provider
        for page in c.pages
    }
    claims = {
        f"{c.attribute}: {c.value}"
        for c in product_claims(round_, names)
        if provider in c.providers
    }
    return Snapshot(
        named=sum(f.named for f in rows),
        answers=sum(f.runs for f in rows),
        best=min(positions) if positions else None,
        rivals={v.name for v in found.rivals if provider in v.providers} if extracted else None,
        cited=pages,
        claims=claims if extracted else None,
    )


def _share(s: Snapshot) -> str:
    best = f", best #{s.best}" if s.best else ""
    return f"{s.named}/{s.answers}{best}"


def _sets(question, provider, kind, old: set[str] | None, new: set[str] | None) -> list[Change]:
    if old is None or new is None:
        if old is None and new is None:
            return []
        return [Change(question, provider, kind, "not comparable: --extract ran on one side only")]
    out = [Change(question, provider, kind, f"new: {x}") for x in sorted(new - old)]
    out += [Change(question, provider, kind, f"gone: {x}") for x in sorted(old - new)]
    return out


def compare(old: Path, new: Path, product: list[str] | None = None) -> list[Change]:
    before, name_old = units(old)
    after, name_new = units(new)
    changes: list[Change] = []
    for question in [q for q in after if q in before]:
        old_round, old_products = before[question]
        new_round, new_products = after[question]
        names = product or (new_products or old_products or [[name_new or name_old]])[0]
        providers = list(dict.fromkeys([r.provider for r in old_round.results + new_round.results]))
        for provider in providers:
            a = snapshot(old_round, names, provider)
            b = snapshot(new_round, names, provider)
            if (a.named, a.answers, a.best) != (b.named, b.answers, b.best):
                changes.append(Change(question, provider, "share", f"{_share(a)} -> {_share(b)}"))
            changes += _sets(question, provider, "rival", a.rivals, b.rivals)
            changes += _sets(question, provider, "cited", a.cited, b.cited)
            changes += _sets(question, provider, "claims", a.claims, b.claims)
    return changes


def unmatched(old: Path, new: Path) -> tuple[list[str], list[str]]:
    """Questions only in the old run, and only in the new one."""
    before, _ = units(old)
    after, _ = units(new)
    return [q for q in before if q not in after], [q for q in after if q not in before]


def latest_pair(out: Path) -> tuple[Path, Path]:
    """The latest run and the one before it of the same set, or of the same question."""
    runs = sorted(
        [*out.glob("*/*/set.json"), *out.glob("*/*/round.json")],
        key=lambda p: (p.parent.parent.name, p.parent.name),
    )
    if not runs:
        raise FileNotFoundError(f"no round under {out}")
    latest = runs[-1]
    key = _key(latest)
    for earlier in reversed(runs[:-1]):
        if _key(earlier) == key:
            return earlier, latest
    raise FileNotFoundError(f"no earlier run of the same questions as {latest.parent.name}")


def _key(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return f"set:{data['product']}" if path.name == "set.json" else f"q:{data['question']}"


def markdown(changes: list[Change], old: Path, new: Path, only: tuple[list[str], list[str]]) -> str:
    lines = ["# What changed", "", f"from {old.parent.name} to {new.parent.name}", ""]
    if not changes:
        lines.append("Nothing changed in the questions both runs asked.")
    by_question: dict[str, list[Change]] = {}
    for change in changes:
        by_question.setdefault(change.question, []).append(change)
    for question, items in by_question.items():
        lines += [f"## {question}", "", "| provider | what | change |", "|---|---|---|"]
        lines += [f"| {c.provider} | {c.kind} | {c.detail} |" for c in items]
        lines.append("")
    gone, added = only
    if gone:
        lines += ["", "Asked before only: " + "; ".join(gone)]
    if added:
        lines += ["", "Asked now only: " + "; ".join(added)]
    return "\n".join(lines).rstrip() + "\n"
