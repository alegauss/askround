"""The products a round's answers recommend, aggregated: the rivals around a product.

Built on the extraction pass (extract.py): each answer's recommendations, in order, are
grouped by a normalised name ("Modly (open-source desktop app)" and "modly" are one),
and counted across runs, providers and locales: in how many answers each appears, at
which ranks, by which providers, with the first quote that recommends it as the reason
given. Products whose name is not in the answer are left out (`mention.standing`), and
so are the names of the product a round is about, which are not its own rivals.

Without the extraction pass there is no list to aggregate: plain text cannot tell a
product from any other capitalised phrase, so `rivals` returns nothing and says why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from askround import mention


def key(name: str) -> str:
    """'Modly (open-source desktop app)' -> 'modly'; 'Reallusion CC - faces' -> 'reallusion cc'."""
    return mention.core(name).lower()


@dataclass
class Rival:
    name: str
    answers: int = 0
    ranks: list[int] = field(default_factory=list)
    providers: dict[str, int] = field(default_factory=dict)
    reason: str = ""

    @property
    def best(self) -> int:
        return min(self.ranks)

    @property
    def mean(self) -> float:
        return sum(self.ranks) / len(self.ranks)


@dataclass
class Rivals:
    rivals: list[Rival]
    # answers whose recommendations were read; the denominator of every count
    read: int
    # why the list is empty when it is: "" when it is not
    missing: str = ""


def rivals(round_, exclude: list[list[str]] | None = None) -> Rivals:
    exclude = exclude or []
    excluded = [mention.pattern(names) for names in exclude]
    table: dict[str, Rival] = {}
    read = 0
    for r in round_.results:
        answer = r.answer
        if answer is None or answer.recommendations is None:
            continue
        read += 1
        seen: set[str] = set()
        for rank, rec in enumerate(mention.standing(answer.text, answer.recommendations), 1):
            if any(p.search(rec.name) for p in excluded):
                continue
            k = key(rec.name)
            if not k or k in seen:
                continue
            seen.add(k)
            rival = table.setdefault(k, Rival(mention.core(rec.name)))
            rival.answers += 1
            rival.ranks.append(rank)
            rival.providers[r.provider] = rival.providers.get(r.provider, 0) + 1
            if not rival.reason and rec.verified:
                rival.reason = rec.quote
    if not read:
        return Rivals([], 0, "rivals are read from the extraction pass: run with --extract")
    ordered = sorted(table.values(), key=lambda v: (-v.answers, v.mean, v.name.lower()))
    return Rivals(ordered, read)
