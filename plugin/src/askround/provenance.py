"""Where a fact came from: the answer's id and the passage's character range.

Every fact askround reports (a mention, a position, a claim) points at the answer it was
read from, by an id that names the provider, the locale and the run (`openai#2`,
`openai@BR#2`), and where it can, at the characters of that answer's text that say it
(`[start, end]`, end excluded). A script or an agent can then cite what it read, and a
claim is one slice away from its passage (law L4).

The JSON askround prints is versioned: each object it prints names its schema
(`askround/round@1`), published in `schema/` in the repository.
"""

from __future__ import annotations

import re

SCHEMA_VERSION = 1


def schema(kind: str) -> str:
    return f"askround/{kind}@{SCHEMA_VERSION}"


def answer_id(result) -> str:
    """'openai#2', or 'openai@BR#2' in a locale."""
    place = f"@{result.locale.country}" if result.locale else ""
    return f"{result.provider}{place}#{result.run}"


def span(text: str, needle: str) -> list[int] | None:
    """Where `needle` is in `text`: exactly, else ignoring case, else with any run of
    whitespace and markdown emphasis between its words; None when it is not there."""
    if not needle:
        return None
    at = text.find(needle)
    if at < 0:
        at = text.lower().find(needle.lower())
    if at >= 0:
        return [at, at + len(needle)]
    words = [re.escape(w) for w in re.split(r"[\s*_`|]+", needle) if w]
    if not words:
        return None
    match = re.search(r"[\s*_`|]+".join(words), text, re.IGNORECASE)
    return [match.start(), match.end()] if match else None
