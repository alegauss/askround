"""No personal data in a question: one round sends the same text to every provider.

A slip in a prompt is a leak to all of them at once, so every question is scanned
before anything is sent, and the run stops naming the question and what was found:

- an email address, a phone number (10 to 15 digits written with separators or a +),
  a Brazilian CPF, an IPv4 address, something shaped like an API key;
- a name from the person's own list of private terms: `ASKROUND_PRIVATE` (comma
  separated) and the file `ASKROUND_PRIVATE_FILE` names (one term per line). The list
  is kept out of the product file on purpose: that file is meant to be shared.

Product names and public domains are fine; a domain is not an email address.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from askround import mention

PATTERNS = {
    "an email address": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "a CPF": re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)"),
    "an IP address": re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    "an API key": re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,})"
    ),
}
_PHONE = re.compile(r"(?<![\w.])\+?\(?\d[\d\s().-]{8,}\d(?![\w.])")


def private_terms() -> list[str]:
    terms = [t.strip() for t in os.environ.get("ASKROUND_PRIVATE", "").split(",")]
    path = os.environ.get("ASKROUND_PRIVATE_FILE")
    if path and Path(path).is_file():
        terms += [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()]
    return [t for t in terms if t and not t.startswith("#")]


def _phones(text: str) -> bool:
    for match in _PHONE.finditer(text):
        found = match.group(0)
        digits = sum(c.isdigit() for c in found)
        separated = found.startswith("+") or any(c in found for c in " ().-")
        if 10 <= digits <= 15 and separated:
            return True
    return False


def scan(text: str, terms: list[str] | None = None) -> list[str]:
    """What personal data the text carries, by kind; empty when there is none."""
    found = [kind for kind, pattern in PATTERNS.items() if pattern.search(text)]
    if _phones(text):
        found.append("a phone number")
    for term in terms if terms is not None else private_terms():
        if mention.pattern([term]).search(text):
            found.append(f"the private term {term!r}")
    return found


def refusal(where: str, text: str, found: list[str]) -> str:
    return (
        f"{where} carries {', '.join(found)}; one round sends it to every provider, so "
        f"nothing was sent: {text!r}"
    )
