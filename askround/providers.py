"""Provider adapters: one question in, one answer out, the raw response kept.

Each adapter is a single HTTPS POST to the provider's own API, read from an API key
in the environment. askround never stores a key: it reads the variable at call time
and writes only the response.

The model is the provider's default below unless `ASKROUND_<NAME>_MODEL` is set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from askround.http import PostJson, post_json


@dataclass
class Answer:
    provider: str
    model: str
    text: str
    raw: dict[str, Any]


class Provider:
    name: str = ""
    key_vars: tuple[str, ...] = ()
    default_model: str = ""

    def __init__(self, post: PostJson = post_json, timeout: float = 300.0):
        self._post = post
        self.timeout = timeout

    @property
    def model(self) -> str:
        return os.environ.get(f"ASKROUND_{self.name.upper()}_MODEL") or self.default_model

    def api_key(self) -> str | None:
        for var in self.key_vars:
            value = os.environ.get(var)
            if value:
                return value
        return None

    def configured(self) -> bool:
        return self.api_key() is not None

    def ask(self, question: str) -> Answer:
        key = self.api_key()
        if key is None:
            raise RuntimeError(f"{self.name}: none of {', '.join(self.key_vars)} is set")
        url, headers, body = self.request(question, key)
        raw = self._post(url, headers, body, self.timeout)
        return Answer(self.name, self.model, self.text(raw), raw)

    def request(self, question: str, key: str) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError

    def text(self, raw: dict[str, Any]) -> str:
        raise NotImplementedError


class OpenAI(Provider):
    """The Responses API, the one that carries ChatGPT's web search tool."""

    name = "openai"
    key_vars = ("OPENAI_API_KEY",)
    default_model = "gpt-5"

    def request(self, question, key):
        return (
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {key}"},
            {"model": self.model, "input": question},
        )

    def text(self, raw):
        parts = []
        for item in raw.get("output") or []:
            if item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))
        return "\n".join(parts).strip()


class Gemini(Provider):
    name = "gemini"
    key_vars = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    default_model = "gemini-2.5-flash"

    def request(self, question, key):
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"x-goog-api-key": key},
            {"contents": [{"role": "user", "parts": [{"text": question}]}]},
        )

    def text(self, raw):
        candidates = raw.get("candidates") or []
        if not candidates:
            return ""
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(part.get("text", "") for part in parts).strip()


class Anthropic(Provider):
    name = "anthropic"
    key_vars = ("ANTHROPIC_API_KEY",)
    default_model = "claude-opus-5-5"

    def request(self, question, key):
        return (
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2026-10-21"},
            {
                "model": self.model,
                "max_tokens": 16000,
                "messages": [{"role": "user", "content": question}],
            },
        )

    def text(self, raw):
        blocks = raw.get("content") or []
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


PROVIDERS: tuple[type[Provider], ...] = (OpenAI, Gemini, Anthropic)


def all_providers(post: PostJson = post_json) -> list[Provider]:
    return [cls(post=post) for cls in PROVIDERS]


def by_name(names: list[str], post: PostJson = post_json) -> list[Provider]:
    known = {cls.name: cls for cls in PROVIDERS}
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(f"unknown provider(s): {', '.join(unknown)}; known: {', '.join(known)}")
    return [known[n](post=post) for n in names]
