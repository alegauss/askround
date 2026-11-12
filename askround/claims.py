"""What a round's answers claim about one product, aggregated.

The extraction pass (extract.py) reads every claim an answer makes about the products
it names, as attribute and value with a verbatim quote. For one product, this groups
them by attribute and value - so 'CPU only: Check build' in two answers is one line
seen twice - with the providers that made each and the first verified quote as its
passage. A claim whose quote is not in the answer is counted apart as unverified,
never mixed with the ones that trace to their passage (law L4).

Attributes are grouped case-insensitively and with whitespace collapsed; the spelling
first seen is the one shown.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from askround import mention


@dataclass
class ProductClaim:
    attribute: str
    value: str
    answers: int = 0
    providers: dict[str, int] = field(default_factory=dict)
    quote: str = ""
    unverified: int = 0


def _fold(text: str) -> str:
    return " ".join(text.lower().split())


def product_claims(round_, names: list[str]) -> list[ProductClaim]:
    target = mention.pattern(names)
    table: dict[tuple[str, str], ProductClaim] = {}
    for r in round_.results:
        answer = r.answer
        if answer is None or not answer.claims:
            continue
        seen: set[tuple[str, str]] = set()
        for claim in answer.claims:
            if not target.search(claim.product):
                continue
            k = (_fold(claim.attribute), _fold(claim.value))
            row = table.setdefault(k, ProductClaim(claim.attribute, claim.value))
            if not claim.verified:
                row.unverified += 1
                continue
            if k in seen:
                continue
            seen.add(k)
            row.answers += 1
            row.providers[r.provider] = row.providers.get(r.provider, 0) + 1
            row.quote = row.quote or claim.quote
    return sorted(table.values(), key=lambda c: (-c.answers, _fold(c.attribute), _fold(c.value)))
