"""A product file: what askround needs to know about one product, kept with it.

    # modelado.toml
    [product]
    name = "Modelado"
    aliases = []                                   # other names it goes by
    places = ["alegauss.github.io/modelado",       # its pages: a domain or a URL prefix
              "github.com/alegauss/modelado"]

    [[fact]]
    attribute = "Runs without an NVIDIA GPU"
    value = "Yes: on the CPU, or any DirectML GPU (AMD, Intel)"
    page = "https://alegauss.github.io/modelado/"  # the page that should say it plainly

A fact is what is true about the product, with the page a reader (and an assistant)
should find it on. `askround ask --product-file modelado.toml` asks about the product
the file describes; with `--extract`, the claims the answers make are compared with its
facts (gaps.py).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Fact:
    attribute: str
    value: str
    page: str = ""


@dataclass
class Product:
    name: str
    aliases: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)

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
    return Product(
        name,
        [str(a) for a in head.get("aliases") or []],
        [str(p) for p in head.get("places") or []],
        facts,
    )
