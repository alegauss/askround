"""Fact gaps: where what the answers claim about a product is not what is true.

On 12/11/2026 an answer wrote 'CPU only: Check build' for Modelado, which runs on the
CPU; the README said so, but not on any first screen. The fix is a sentence on the page
an assistant reads, so a gap names the claim, the fact it gets wrong, the page that
should state the fact plainly (the fact's `page` in the product file) and the product's
pages the answers did cite.

Matching words cannot tell 'Check build' from 'Yes', so the comparison is one
structured call per product per round, on the extractor's provider: the round's claims
about the product (aggregated, each with its verified passage) against the product
file's facts. Each claim comes back as agrees, contradicts, doubts (the answer hedges
or leaves the reader unsure) or unrelated, tied to the fact it concerns. Only claims
whose passage was found in an answer are compared (law L4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from askround import citations
from askround.claims import ProductClaim, product_claims
from askround.product import Product

VERDICTS = ("agrees", "contradicts", "doubts", "unrelated")

PROMPT = """Below are facts about the product "{name}", as its maker states them, and claims that AI assistants made about it in their answers.

Many claims come from comparison tables, where the attribute is a column header that asks a question and the value is the answer's reply to it: "CPU only: Yes" means "it works with only a CPU", "CPU only: Check build" means "unsure whether it works with only a CPU". Read each claim that way.

For each claim, say which fact it concerns (its number, or 0 if none) and whether it agrees with that fact, contradicts it, doubts it (hedges, says to check, or leaves a reader unsure of something the fact states plainly), or is unrelated to every fact. Give one short sentence of why.

<facts>
{facts}
</facts>

<claims>
{claims}
</claims>"""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "integer"},
                    "fact": {"type": "integer"},
                    "verdict": {"type": "string", "enum": list(VERDICTS)},
                    "why": {"type": "string"},
                },
                "required": ["claim", "fact", "verdict", "why"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


@dataclass
class Gap:
    attribute: str  # the claim, as the answers made it
    value: str
    quote: str
    providers: dict[str, int]
    verdict: str  # contradicts or doubts
    why: str
    fact: str  # the fact it gets wrong: "attribute: value"
    page: str  # where the fact should be stated plainly
    cited: list[str] = field(default_factory=list)  # the product's pages the answers cited


def _cited(round_, product: Product) -> list[str]:
    rows = citations.product_citations(round_, product.names) if product.places else []
    return sorted({page for row in rows for page in row.pages})


def compare(round_, product: Product, extractor) -> list[Gap]:
    """The gaps between the round's claims about the product and its facts."""
    claims: list[ProductClaim] = [c for c in product_claims(round_, product.names) if c.answers]
    if not claims or not product.facts:
        return []
    facts = "\n".join(f"{i}. {f.attribute}: {f.value}" for i, f in enumerate(product.facts, 1))
    listed = "\n".join(
        f'{i}. {c.attribute}: {c.value} (passage: "{c.quote}")' for i, c in enumerate(claims, 1)
    )
    prompt = PROMPT.format(name=product.name, facts=facts, claims=listed)
    data = extractor.ask_json(prompt, SCHEMA)
    cited = _cited(round_, product)
    gaps = []
    for item in data.get("verdicts") or []:
        verdict = item.get("verdict")
        c, f = item.get("claim", 0), item.get("fact", 0)
        if verdict not in ("contradicts", "doubts"):
            continue
        if not (1 <= c <= len(claims) and 1 <= f <= len(product.facts)):
            continue
        claim, fact = claims[c - 1], product.facts[f - 1]
        gaps.append(
            Gap(
                claim.attribute,
                claim.value,
                claim.quote,
                dict(claim.providers),
                verdict,
                str(item.get("why") or ""),
                f"{fact.attribute}: {fact.value}",
                fact.page,
                cited,
            )
        )
    return gaps
