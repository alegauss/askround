"""The extraction pass: what an answer recommends, in its order, each with its passage.

Plain text matching (`mention.py`) sees list items and table rows; it cannot tell that
"Best fit" in a table's last column or "my first choice" in a paragraph puts a product
first. So a model reads each answer once, with a JSON schema, and returns the products
the answer recommends in the order it recommends them, each with a short verbatim quote.
The list does not depend on any product asked about: a product's rank is where it falls
in it, and the same list names the rivals around it.

Plain text is the check (law L4, every fact traces to its passage): a recommendation
whose quote is not in the answer is kept but marked unverified and does not rank, and a
product counts as named only when its name is in the answer's text, whatever the model
said. The pass costs one call per answer, so it runs only when asked for (`--extract`).

The extractor is whichever provider is configured, first of OpenAI, Gemini and
Anthropic, on a small model (`ASKROUND_EXTRACT_MODEL` overrides it).
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from askround.http import ATTEMPTS, PostJson, post_json, with_retries
from askround.providers import Anthropic, Gemini, OpenAI

INSTRUCTIONS = """You read one answer an AI assistant gave to a user, and list what it recommends.

List every product, app, tool, model or service the answer recommends or suggests to the user, in the answer's order of preference: first the one it presents as its top pick ("best fit", "my first choice", "start with", the first item of its list or table), then the rest in the order the answer gives them. Include products recommended inside tables. Leave out products the answer mentions only to rule them out.

For each, give its name exactly as the answer writes it, and a short quote copied verbatim from the answer (one phrase or table row, at most 25 words) that recommends it. Do not add products the answer does not name. If it recommends nothing, return an empty list."""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["name", "quote"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["recommendations"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Recommendation:
    name: str
    quote: str
    verified: bool


def _squash(text: str) -> str:
    """Lower case, markdown emphasis and table bars dropped, whitespace collapsed:
    a quote copied from a table row or a bold phrase still matches its passage."""
    text = re.sub(r"[*_`|]+", " ", text.lower())
    return " ".join(text.split())


def verify(answer_text: str, items: list[dict]) -> list[Recommendation]:
    haystack = _squash(answer_text)
    out = []
    for item in items:
        name = str(item.get("name", "")).strip()
        quote = str(item.get("quote", "")).strip()
        if not name:
            continue
        verified = bool(quote) and _squash(quote) in haystack
        out.append(Recommendation(name, quote, verified))
    return out


class Extractor:
    """One structured-output call per answer, on one provider's API."""

    provider: type
    default_model: str = ""

    def __init__(self, post: PostJson = post_json, timeout: float = 120.0):
        self._post = with_retries(post, ATTEMPTS)
        self.timeout = timeout
        self._source = self.provider(post=post)

    @property
    def name(self) -> str:
        return self.provider.name

    @property
    def model(self) -> str:
        return os.environ.get("ASKROUND_EXTRACT_MODEL") or self.default_model

    def configured(self) -> bool:
        return self._source.configured()

    def recommendations(self, answer_text: str) -> list[Recommendation]:
        key = self._source.api_key()
        if key is None:
            raise RuntimeError(f"{self.name}: no API key for the extraction pass")
        prompt = f"{INSTRUCTIONS}\n\n<answer>\n{answer_text}\n</answer>"
        url, headers, body = self.request(prompt, key)
        raw = self._post(url, headers, body, self.timeout)
        data = json.loads(self.json_text(raw))
        return verify(answer_text, data.get("recommendations") or [])

    def request(self, prompt: str, key: str) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError

    def json_text(self, raw: dict[str, Any]) -> str:
        raise NotImplementedError


class OpenAIExtractor(Extractor):
    provider = OpenAI
    default_model = "gpt-5-mini"

    def request(self, prompt, key):
        return (
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {key}"},
            {
                "model": self.model,
                "input": prompt,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "recommendations",
                        "schema": SCHEMA,
                        "strict": True,
                    }
                },
            },
        )

    def json_text(self, raw):
        return OpenAI().parse(raw).text


class GeminiExtractor(Extractor):
    provider = Gemini
    default_model = "gemini-2.5-flash"

    def request(self, prompt, key):
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"x-goog-api-key": key},
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": SCHEMA,
                },
            },
        )

    def json_text(self, raw):
        return Gemini().parse(raw).text


class AnthropicExtractor(Extractor):
    provider = Anthropic
    default_model = "claude-haiku-5-5"

    def request(self, prompt, key):
        return (
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2026-10-21"},
            {
                "model": self.model,
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}],
                "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
            },
        )

    def json_text(self, raw):
        return Anthropic().parse(raw).text


EXTRACTORS: tuple[type[Extractor], ...] = (OpenAIExtractor, GeminiExtractor, AnthropicExtractor)


def choose(name: str = "auto", post: PostJson = post_json) -> Extractor:
    """The extractor named, or with "auto" the first whose provider has a key."""
    candidates = [cls(post=post) for cls in EXTRACTORS]
    if name != "auto":
        chosen = [c for c in candidates if c.name == name]
        if not chosen:
            known = ", ".join(c.name for c in candidates)
            raise ValueError(f"no extractor for {name!r}; known: {known}")
        return chosen[0]
    for candidate in candidates:
        if candidate.configured():
            return candidate
    raise ValueError("the extraction pass needs an OpenAI, Gemini or Anthropic key")


def extract_round(round_, extractor: Extractor, parallel: int = 8) -> None:
    """Fill `recommendations` (or `extraction_error`) on every answer of the round."""
    answers = [r.answer for r in round_.results if r.answer is not None]

    def one(answer) -> None:
        try:
            answer.recommendations = extractor.recommendations(answer.text)
            answer.extracted_by = f"{extractor.name}:{extractor.model}"
        except Exception as error:  # noqa: BLE001 - the plain-text reading still stands
            answer.extraction_error = f"{type(error).__name__}: {error}"[:300]

    with ThreadPoolExecutor(max_workers=max(1, min(len(answers), parallel))) as pool:
        list(pool.map(one, answers))
