"""Discovery: which way of asking leads an assistant to the product.

On 12/11/2026 it took four questions by hand to find that the generic one never named
Modelado and the 'without an NVIDIA GPU' one put it first - which told who the app is
for and what to say on its first screen. Discovery does that search:

1. From a seed question and the product file's facts, a model writes variants along
   each axis - a constraint the product meets, a use case it serves, another language -
   none of them naming the product. A variant that names it (or one of its places) is
   dropped: a question that names the product measures nothing. So is one that carries
   personal data (private.py), which the model could have copied from the facts.
2. The seed and the variants run as a prompt set (sets.py).
3. Each question is scored over all its answers: 1/position where the product is in the
   answer's recommendations, 1/2 where it is named outside them, 0 where it is absent;
   the questions are ranked by that score.

The generation is one structured call on the extractor's provider; the run costs what
a prompt set of that many questions costs, so discovery defaults to one run each, and
a question worth keeping is then added to the product file and run again with more.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from askround import mention, private
from askround.product import Product, Question
from askround.providers import Locale
from askround.round import Round, frequency

AXES = ("constraint", "use case", "language")

PROMPT = """You help test how AI assistants answer people looking for software. A seed question is below, with facts about one product. Write {n} new questions a real person might type into an assistant, each a variant of the seed along one axis:

- constraint: the seed plus a requirement the product meets (from the facts), as the person would state it;
- use case: the seed narrowed to a task the product serves;
- language: the seed, or a constraint variant, written in another language its users speak ({languages}).

Never name the product, its maker or its website; the questions must leave the assistant free to recommend anything. Spread the variants across the axes. For a language variant give the locale as COUNTRY:language (e.g. BR:pt-BR), otherwise leave it empty.

<seed>{seed}</seed>

<facts>
{facts}
</facts>"""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "axis": {"type": "string", "enum": list(AXES)},
                    "locale": {"type": "string"},
                },
                "required": ["text", "axis", "locale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}


def generate(
    seed: str, product: Product, extractor, n: int = 6, languages: str = "Portuguese (Brazil)"
) -> tuple[list[Question], list[str]]:
    """The variants, and the ones dropped for naming the product."""
    facts = "\n".join(f"- {f.attribute}: {f.value}" for f in product.facts) or "- (none given)"
    prompt = PROMPT.format(n=n, seed=seed, facts=facts, languages=languages)
    data = extractor.ask_json(prompt, SCHEMA)
    names = mention.pattern(product.names)
    kept: list[Question] = []
    dropped: list[str] = []
    for item in data.get("questions") or []:
        text = str(item.get("text") or "").strip()
        if not text or text == seed:
            continue
        if names.search(text) or private.scan(text):
            dropped.append(text)
            continue
        try:
            locale = Locale.parse(item["locale"]) if item.get("locale") else None
        except ValueError:
            locale = None
        kept.append(Question(text, str(item.get("axis") or ""), locale))
    return kept, dropped


@dataclass(frozen=True)
class Ranked:
    question: Question
    score: float
    named: int
    answers: int
    best: int | None


def score(round_: Round, names: list[str]) -> tuple[float, int, int, int | None]:
    """The mean over every answer of 1/position, 1/2 if named outside the list, else 0."""
    total, named, answers, best = 0.0, 0, 0, None
    for row in frequency(round_, names):
        answers += row.runs
        named += row.named
        for position in row.positions:
            if position is not None:
                total += 1 / position
                best = position if best is None else min(best, position)
        unplaced = row.named - sum(p is not None for p in row.positions)
        total += 0.5 * unplaced
    return (total / answers if answers else 0.0), named, answers, best


def rank(questions: list[Question], rounds: list[Round], names: list[str]) -> list[Ranked]:
    ranked = []
    for question, round_ in zip(questions, rounds, strict=True):
        value, named, answers, best = score(round_, names)
        ranked.append(Ranked(question, value, named, answers, best))
    return sorted(ranked, key=lambda r: -r.score)
