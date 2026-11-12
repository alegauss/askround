"""Research mode: one question to every assistant with search, the answers merged.

Beyond whether a product is named, the session that started askround needed research
(which open image-to-3D models allow commercial use, which competitors exist), done by
separate searches and reading, marking what was verified against what was inferred.
`askround research` asks every provider once with search, then merges:

1. each answer is read for the factual statements it makes, each with a verbatim quote
   checked against the answer (law L4);
2. one call groups the statements that say the same thing across answers, so each
   merged claim lists the providers that support it, with their passages;
3. each claim's sources are those its supporting answers cited - an answer cites pages
   for all its claims at once, so the pages whose address names the claim's subject
   come first, and among them the primary ones: a repository, a licence text, a paper
   or a project's own documentation, before the blogs, news and lists about them.

Claims are ranked by how many providers support them. Support is agreement among
assistants, not proof: a claim with a primary source is the one to check at the source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from askround import citations
from askround.extract import _squash

READ = """Below is one answer an AI assistant gave to a research question. List the factual statements it makes that bear on the question - each a single, self-contained claim (who, what, which licence, which number), not advice or opinion. For each, give the statement in your own short words and a quote copied verbatim from the answer that makes it (at most 30 words).

<question>{question}</question>

<answer>
{answer}
</answer>"""

READ_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "statements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"statement": {"type": "string"}, "quote": {"type": "string"}},
                "required": ["statement", "quote"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["statements"],
    "additionalProperties": False,
}

MERGE = """Below are statements that several AI assistants made in answer to one research question, each with an id. Group the statements that make the same claim (the same fact about the same subject, even worded differently) and write each group's claim once, in plain words. Every id belongs to exactly one group; a statement no other statement repeats is a group of one. Do not merge statements that disagree: two different values for the same fact are two claims. Do not merge statements about different subjects, even when their names are alike (two models, versions or products with similar names are different subjects).

<question>{question}</question>

<statements>
{statements}
</statements>"""

MERGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["claim", "ids"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}

PRIMARY_HOSTS = ("github.com", "gitlab.com", "huggingface.co", "arxiv.org", "pypi.org", "npmjs.com")


@dataclass(frozen=True)
class Statement:
    id: str  # "<provider>#<run>:<n>"
    provider: str
    statement: str
    quote: str
    sources: tuple[str, ...]


@dataclass
class Merged:
    claim: str
    providers: list[str]
    passages: dict[str, str]  # provider -> one quote
    sources: list[dict] = field(default_factory=list)  # {url, primary}


def primary(url: str) -> bool:
    """A repository, a licence text, a paper or a project's own documentation."""
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.lower()
    if any(host == h or host.endswith("." + h) for h in PRIMARY_HOSTS):
        return True
    if "licen" in path or path.endswith((".pdf", "/license", "/copying")):
        return True
    return host.startswith("docs.") or "/docs" in path


def read(round_, extractor) -> list[Statement]:
    """Every verified statement of every answer, with that answer's cited pages."""
    out: list[Statement] = []
    for r in round_.results:
        answer = r.answer
        if answer is None or not answer.text:
            continue
        data = extractor.ask_json(
            READ.format(question=round_.question, answer=answer.text), READ_SCHEMA
        )
        haystack = _squash(answer.text)
        pages = tuple(p.url for p in citations.cited(answer))
        n = 0
        for item in data.get("statements") or []:
            quote = str(item.get("quote") or "").strip()
            text = str(item.get("statement") or "").strip()
            if not text or not quote or _squash(quote) not in haystack:
                continue  # a statement not traced to its passage is not kept
            n += 1
            out.append(Statement(f"{r.provider}#{r.run}:{n}", r.provider, text, quote, pages))
    return out


def merge(question: str, statements: list[Statement], extractor) -> list[Merged]:
    if not statements:
        return []
    listed = "\n".join(f"{s.id}: {s.statement}" for s in statements)
    data = extractor.ask_json(MERGE.format(question=question, statements=listed), MERGE_SCHEMA)
    by_id = {s.id: s for s in statements}
    placed: set[str] = set()
    merged: list[Merged] = []
    for group in data.get("claims") or []:
        members = [by_id[i] for i in group.get("ids") or [] if i in by_id and i not in placed]
        if not members:
            continue
        placed.update(m.id for m in members)
        merged.append(_merged(str(group.get("claim") or members[0].statement), members))
    # a statement the model left out of every group still counts, on its own
    merged += [_merged(s.statement, [s]) for s in statements if s.id not in placed]
    merged.sort(
        key=lambda m: (-len(m.providers), -sum(s["primary"] and s["about"] for s in m.sources))
    )
    return merged


def _merged(claim: str, members: list[Statement]) -> Merged:
    providers = list(dict.fromkeys(m.provider for m in members))
    passages = {}
    for m in members:
        passages.setdefault(m.provider, m.quote)
    urls = list(dict.fromkeys(url for m in members for url in m.sources))
    words = _subject_words(claim)
    sources = [
        {"url": u, "primary": primary(u), "about": any(w in u.lower() for w in words)} for u in urls
    ]
    # an answer cites pages for all its claims: the ones naming this claim's subject first
    sources.sort(key=lambda s: (not s["about"], not s["primary"]))
    return Merged(claim, providers, passages, sources)


_COMMON = {
    "license",
    "licence",
    "commercial",
    "allowed",
    "under",
    "with",
    "model",
    "models",
    "open",
    "source",
    "released",
    "weights",
}


def _subject_words(claim: str) -> list[str]:
    """The distinctive words of a claim (names, mostly), to match against addresses."""
    tokens = [t.strip(".,;:()'\"").lower() for t in claim.split()]
    return [t for t in tokens if len(t) >= 4 and t not in _COMMON]


def markdown(question: str, merged: list[Merged], providers: list[str]) -> str:
    lines = [f"# Research: {question}", ""]
    lines.append(
        f"{len(merged)} claims from {len(providers)} providers ({', '.join(providers)}), "
        "most supported first. Support is agreement among assistants, not proof; check a "
        "claim at its primary source."
    )
    lines.append("")
    for n, m in enumerate(merged, 1):
        lines.append(f"## {n}. {m.claim}")
        lines.append("")
        lines.append(f"Supported by {len(m.providers)}/{len(providers)}: {', '.join(m.providers)}")
        for provider, quote in m.passages.items():
            lines.append(f'- {provider}: "{quote}"')
        if m.sources:
            lines.append("")
            lines.append("Sources:")
            for s in m.sources[:6]:
                tag = "primary" if s["primary"] else "secondary"
                lines.append(f"- [{tag}] {s['url']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def as_json(merged: list[Merged]) -> list[dict]:
    return [m.__dict__ for m in merged]
