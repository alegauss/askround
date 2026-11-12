"""A product file: what askround needs to know about one product, kept with it.

    # modelado.toml
    [product]
    name = "Modelado"
    aliases = []                                   # other names it goes by
    places = ["alegauss.github.io/modelado",       # its pages: a domain or a URL prefix
              "github.com/alegauss/modelado"]
    phrases = ["a photo becomes a 3D model"]       # its own wording, kept out of questions

    [[fact]]
    attribute = "Runs without an NVIDIA GPU"
    value = "Yes: on the CPU, or any DirectML GPU (AMD, Intel)"
    page = "https://alegauss.github.io/modelado/"  # the page that should say it plainly

    [[question]]
    text = "What app can turn a photo into a 3D model on Windows without an NVIDIA GPU?"
    purpose = "constraint"       # generic, constraint, use case, language: why it is asked
    locale = "BR:pt-BR"          # optional: asked as someone in this country
    runs = 3                     # optional: the round's default otherwise
    brand = false                # true: it names the product on purpose, reported apart

A fact is what is true about the product, with the page a reader (and an assistant)
should find it on. `askround ask --product-file modelado.toml` asks about the product
the file describes; with `--extract`, the claims the answers make are compared with its
facts (gaps.py). The questions make the file a prompt set: `askround run modelado.toml`
asks them all, the same way every time, so next week's answers can be set beside this
week's.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from askround.providers import Locale


@dataclass(frozen=True)
class Fact:
    attribute: str
    value: str
    page: str = ""


@dataclass(frozen=True)
class Question:
    text: str
    purpose: str = ""
    locale: Locale | None = None
    runs: int | None = None
    # asks about the product on purpose, so it may name it; reported apart (leading.py)
    brand: bool = False


@dataclass
class Product:
    name: str
    aliases: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    # wording distinctive of the product's own pages, which a neutral question avoids
    phrases: list[str] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        """The names askround matches it by: name, aliases, then its places."""
        return [self.name, *self.aliases, *self.places]


def load(path: Path) -> Product:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path}: {error}") from None
    head = data.get("product") or {}
    name = str(head.get("name") or "").strip()
    if not name:
        raise ValueError(f"{path}: [product] needs a name")
    facts = []
    for i, item in enumerate(data.get("fact") or [], start=1):
        attribute = str(item.get("attribute") or "").strip()
        value = str(item.get("value") or "").strip()
        if not attribute or not value:
            raise ValueError(f"{path}: fact {i} needs an attribute and a value")
        facts.append(Fact(attribute, value, str(item.get("page") or "").strip()))
    questions = [_question(path, i, item) for i, item in enumerate(data.get("question") or [], 1)]
    return Product(
        name,
        [str(a) for a in head.get("aliases") or []],
        [str(p) for p in head.get("places") or []],
        facts,
        questions,
        [str(p) for p in head.get("phrases") or []],
    )


def _question(path: Path, i: int, item: dict) -> Question:
    text = str(item.get("text") or "").strip()
    if not text:
        raise ValueError(f"{path}: question {i} needs a text")
    try:
        locale = Locale.parse(str(item["locale"])) if item.get("locale") else None
    except ValueError as error:
        raise ValueError(f"{path}: question {i}: {error}") from None
    runs = item.get("runs")
    if runs is not None and (not isinstance(runs, int) or runs < 1):
        raise ValueError(f"{path}: question {i}: runs must be a whole number of at least 1")
    brand = item.get("brand", False)
    if not isinstance(brand, bool):
        raise ValueError(f"{path}: question {i}: brand must be true or false")
    return Question(text, str(item.get("purpose") or "").strip(), locale, runs, brand)
