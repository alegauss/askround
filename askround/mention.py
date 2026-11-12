"""Whether an answer names a product, and where, by plain text matching.

A product is given by its names (the first is how it is reported, the rest are aliases).
A name matches case-insensitively on word boundaries, so "Modelado" does not match
"Modelados3D".

The position is the product's place among the answer's recommendation lines: top-level
numbered or bulleted items, numbered headings and table rows, the shapes assistants
recommend in. The
product's position is the index of the first such line that names it, so "2" reads
as "the second thing recommended". A product named only in prose has no position.

This is the plain-text half of reading an answer. A structured extraction pass
(AR8) is meant to be checked against it, so that a table cell marked 'Best fit' and
'my first choice' in prose count as well; this module never calls a model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ITEM = re.compile(r"^[ \t]*(?:\d+[.)] |[-*+•] |#{1,6} \**\d+[.)])")
_TABLE_RULE = re.compile(r"^[ \t]*(?:\|[ \t]*)?:?-{3}")


@dataclass(frozen=True)
class Mention:
    named: bool
    position: int | None = None


def _pattern(names: list[str]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE)


def recommendation_lines(text: str) -> list[str]:
    """Top-level list items, numbered headings and table body rows, in order.

    Sub-items (indented deeper than the shallowest item) are details of the item
    above, not recommendations of their own, and a table's header row is not one.
    """
    lines = text.splitlines()
    items: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if _TABLE_RULE.match(line):
            continue
        indent = len(line) - len(line.lstrip())
        if line.lstrip().startswith("|"):
            is_header = i + 1 < len(lines) and _TABLE_RULE.match(lines[i + 1])
            if not is_header:
                items.append((indent, line))
        elif _ITEM.match(line):
            items.append((indent, line))
    if not items:
        return []
    top = min(indent for indent, _ in items)
    return [line for indent, line in items if indent == top]


def find(text: str, names: list[str]) -> Mention:
    if not names:
        raise ValueError("a product needs at least one name")
    pattern = _pattern(names)
    if not pattern.search(text):
        return Mention(False)
    for index, line in enumerate(recommendation_lines(text), start=1):
        if pattern.search(line):
            return Mention(True, index)
    return Mention(True)
