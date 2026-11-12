"""Provider adapters: one question in, one answer out, the raw response kept.

Each adapter is a single HTTPS POST to the provider's own API, read from an API key
in the environment. askround never stores a key: it reads the variable at call time
and writes only the response.

Web search is on by default, through each provider's own tool: OpenAI's Responses API
`web_search` tool, Gemini's grounding with Google Search, Anthropic's web search server
tool, and Perplexity's Sonar models, which search unless told not to. Assistants
recommend products through search, so a round without it measures something no user
sees; `search=False` is there to compare against. Each answer keeps the search queries
and the sources the provider reported, as the provider reported them (Gemini's are
redirect links titled with the domain).

A question can be asked as someone in a country and language would ask it (`Locale`).
Each API takes a different part of that, and only for its search: OpenAI, Anthropic and
Perplexity an approximate country, Gemini a language for its Google Search retrieval.
What an API cannot take is recorded on the answer as ignored, never silently dropped;
the language of the question itself is still the strongest signal and is the caller's.

The model is the provider's default below unless `ASKROUND_<NAME>_MODEL` is set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from askround.http import ATTEMPTS, PostJson, post_json, with_retries


@dataclass(frozen=True)
class Source:
    url: str
    title: str = ""


@dataclass(frozen=True)
class Locale:
    """Where and in which language the asker is: an ISO 3166 country code ("BR") and
    an optional BCP 47 language tag ("pt-BR")."""

    country: str
    language: str | None = None

    @classmethod
    def parse(cls, value: str) -> Locale:
        country, _, language = value.partition(":")
        country = country.strip().upper()
        if len(country) != 2 or not country.isalpha():
            raise ValueError(f"{value!r}: expected COUNTRY[:LANGUAGE], e.g. BR:pt-BR")
        return cls(country, language.strip() or None)

    def __str__(self) -> str:
        return f"{self.country}:{self.language}" if self.language else self.country


@dataclass
class Answer:
    """One answer and what produced it.

    `model` is the id askround asked for and `served_model` the id the API says
    answered, which is where a silent model update shows. `settings` is the request
    as sent minus the question (model, tools, include, max_tokens, ...), so a change
    in how askround asks can be told from a change in what the provider answers.
    """

    provider: str
    model: str
    text: str
    raw: dict[str, Any]
    search: bool = True
    sources: list[Source] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    served_model: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    answered_at: datetime | None = None
    locale: Locale | None = None
    # the parts of `locale` this provider's API could not take, e.g. ["language"]
    locale_ignored: list[str] = field(default_factory=list)
    # filled by the extraction pass (extract.py); None where it did not run
    recommendations: list[Any] | None = None
    claims: list[Any] | None = None
    extracted_by: str = ""
    extraction_error: str | None = None


@dataclass
class Parsed:
    text: str
    sources: list[Source] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)


# the request fields that carry the question, left out of an answer's recorded settings
QUESTION_FIELDS = ("input", "messages", "contents")


class Provider:
    name: str = ""
    key_vars: tuple[str, ...] = ()
    default_model: str = ""
    # how the adapter searches, as `askround doctor` reports it
    search_tool: str = ""
    # the Locale fields this API takes, and only when searching
    locale_fields: tuple[str, ...] = ()

    def __init__(
        self,
        post: PostJson = post_json,
        timeout: float = 300.0,
        model: str | None = None,
        attempts: int = ATTEMPTS,
    ):
        # every call is retried on a rate limit, a server error or a timeout
        self._post = with_retries(post, attempts)
        self.timeout = timeout
        self._model = model

    @property
    def model(self) -> str:
        """Pinned with `model=`, else `ASKROUND_<NAME>_MODEL`, else the default."""
        return (
            self._model
            or os.environ.get(f"ASKROUND_{self.name.upper()}_MODEL")
            or self.default_model
        )

    def served_model(self, raw: dict[str, Any]) -> str:
        """The model id the response says answered; most APIs call the field `model`."""
        return str(raw.get("model") or "")

    def api_key(self) -> str | None:
        for var in self.key_vars:
            value = os.environ.get(var)
            if value:
                return value
        return None

    def configured(self) -> bool:
        return self.api_key() is not None

    def key_var(self) -> str | None:
        """The name of the variable the key is read from, never its value."""
        return next((var for var in self.key_vars if os.environ.get(var)), None)

    def check(self) -> None:
        """The cheapest call that proves the key and the model work; raises if not."""
        key = self.api_key()
        if key is None:
            raise RuntimeError(f"{self.name}: none of {', '.join(self.key_vars)} is set")
        url, headers, body = self.check_request(key)
        self._post(url, headers, body, min(self.timeout, 30.0))

    def check_request(self, key: str) -> tuple[str, dict[str, str], dict[str, Any] | None]:
        raise NotImplementedError

    def locale_ignored(self, locale: Locale | None, search: bool) -> list[str]:
        if locale is None:
            return []
        asked = ["country"] + (["language"] if locale.language else [])
        taken = self.locale_fields if search else ()
        return [part for part in asked if part not in taken]

    def ask(self, question: str, search: bool = True, locale: Locale | None = None) -> Answer:
        key = self.api_key()
        if key is None:
            raise RuntimeError(f"{self.name}: none of {', '.join(self.key_vars)} is set")
        _, _, body = self.request(question, key, search, locale)
        settings = {k: v for k, v in body.items() if k not in QUESTION_FIELDS}
        raw = self.call(question, key, search, locale)
        parsed = self.parse(raw)
        return Answer(
            self.name,
            self.model,
            parsed.text,
            raw,
            search=search,
            sources=_unique(parsed.sources),
            queries=list(dict.fromkeys(q for q in parsed.queries if q)),
            served_model=self.served_model(raw) or self.model,
            settings=settings,
            answered_at=datetime.now(UTC),
            locale=locale,
            locale_ignored=self.locale_ignored(locale, search),
        )

    def call(
        self, question: str, key: str, search: bool, locale: Locale | None = None
    ) -> dict[str, Any]:
        url, headers, body = self.request(question, key, search, locale)
        return self._post(url, headers, body, self.timeout)

    def request(
        self, question: str, key: str, search: bool, locale: Locale | None = None
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError

    def parse(self, raw: dict[str, Any]) -> Parsed:
        raise NotImplementedError


def _unique(sources: list[Source]) -> list[Source]:
    seen: dict[str, Source] = {}
    for source in sources:
        if source.url and source.url not in seen:
            seen[source.url] = source
    return list(seen.values())


class OpenAI(Provider):
    """The Responses API, the one that carries ChatGPT's web search tool."""

    name = "openai"
    key_vars = ("OPENAI_API_KEY",)
    default_model = "gpt-5"
    search_tool = "web_search (Responses API)"
    locale_fields = ("country",)

    def check_request(self, key):
        return (
            f"https://api.openai.com/v1/models/{self.model}",
            {"Authorization": f"Bearer {key}"},
            None,
        )

    def request(self, question, key, search, locale=None):
        body: dict[str, Any] = {"model": self.model, "input": question}
        if search:
            tool: dict[str, Any] = {"type": "web_search"}
            if locale:
                tool["user_location"] = {"type": "approximate", "country": locale.country}
            body["tools"] = [tool]
            body["include"] = ["web_search_call.action.sources"]
        return (
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {key}"},
            body,
        )

    def parse(self, raw):
        parts: list[str] = []
        sources: list[Source] = []
        queries: list[str] = []
        for item in raw.get("output") or []:
            kind = item.get("type")
            if kind == "web_search_call":
                action = item.get("action") or {}
                queries.append(action.get("query", ""))
                queries.extend(action.get("queries") or [])
            elif kind == "message":
                for content in item.get("content") or []:
                    if content.get("type") != "output_text":
                        continue
                    parts.append(content.get("text", ""))
                    for note in content.get("annotations") or []:
                        if note.get("type") == "url_citation":
                            sources.append(Source(note.get("url", ""), note.get("title", "")))
        return Parsed("\n".join(parts).strip(), sources, queries)


class Gemini(Provider):
    name = "gemini"
    key_vars = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    default_model = "gemini-2.5-flash"
    search_tool = "google_search grounding"
    locale_fields = ("language",)

    def check_request(self, key):
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}",
            {"x-goog-api-key": key},
            None,
        )

    def request(self, question, key, search, locale=None):
        body: dict[str, Any] = {"contents": [{"role": "user", "parts": [{"text": question}]}]}
        if search:
            body["tools"] = [{"google_search": {}}]
            if locale and locale.language:
                body["toolConfig"] = {"retrievalConfig": {"languageCode": locale.language}}
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"x-goog-api-key": key},
            body,
        )

    def served_model(self, raw):
        return str(raw.get("modelVersion") or "")

    def parse(self, raw):
        candidates = raw.get("candidates") or []
        if not candidates:
            return Parsed("")
        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
        grounding = candidate.get("groundingMetadata") or {}
        sources = [
            Source(chunk["web"].get("uri", ""), chunk["web"].get("title", ""))
            for chunk in grounding.get("groundingChunks") or []
            if chunk.get("web")
        ]
        return Parsed(text, sources, list(grounding.get("webSearchQueries") or []))


class Anthropic(Provider):
    name = "anthropic"
    key_vars = ("ANTHROPIC_API_KEY",)
    default_model = "claude-opus-5-5"
    search_tool = "web_search_20260209 server tool"
    locale_fields = ("country",)
    # a searching turn can pause server-side; it is resumed by sending it back
    max_continuations = 3

    def check_request(self, key):
        return (
            f"https://api.anthropic.com/v1/models/{self.model}",
            {"x-api-key": key, "anthropic-version": "2026-10-21"},
            None,
        )

    def request(self, question, key, search, locale=None):
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 16000,
            "messages": [{"role": "user", "content": question}],
        }
        if search:
            tool: dict[str, Any] = {"type": "web_search_20260209", "name": "web_search"}
            if locale:
                tool["user_location"] = {"type": "approximate", "country": locale.country}
            body["tools"] = [tool]
        return (
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2026-10-21"},
            body,
        )

    def call(self, question, key, search, locale=None):
        url, headers, body = self.request(question, key, search, locale)
        turns = [self._post(url, headers, body, self.timeout)]
        while turns[-1].get("stop_reason") == "pause_turn" and len(turns) <= self.max_continuations:
            body = {
                **body,
                "messages": [
                    *body["messages"],
                    {"role": "assistant", "content": turns[-1].get("content") or []},
                ],
            }
            turns.append(self._post(url, headers, body, self.timeout))
        return turns[0] if len(turns) == 1 else {"turns": turns}

    def served_model(self, raw):
        last = (raw.get("turns") or [raw])[-1]
        return str(last.get("model") or "")

    def parse(self, raw):
        turns = raw.get("turns") or [raw]
        parts: list[str] = []
        sources: list[Source] = []
        queries: list[str] = []
        for turn in turns:
            for block in turn.get("content") or []:
                kind = block.get("type")
                if kind == "text":
                    parts.append(block.get("text", ""))
                    for cite in block.get("citations") or []:
                        if cite.get("url"):
                            sources.append(Source(cite["url"], cite.get("title") or ""))
                elif kind == "server_tool_use" and block.get("name") == "web_search":
                    queries.append((block.get("input") or {}).get("query", ""))
                elif kind == "web_search_tool_result" and isinstance(block.get("content"), list):
                    for result in block["content"]:
                        if result.get("url"):
                            sources.append(Source(result["url"], result.get("title") or ""))
        return Parsed("".join(parts).strip(), sources, queries)


class Perplexity(Provider):
    """Sonar models search by default; `disable_search` turns that off."""

    name = "perplexity"
    key_vars = ("PERPLEXITY_API_KEY",)
    default_model = "sonar"
    search_tool = "built into Sonar"
    locale_fields = ("country",)

    def check_request(self, key):
        # no free model lookup: one token, search off, is the cheapest proof
        return (
            "https://api.perplexity.ai/chat/completions",
            {"Authorization": f"Bearer {key}"},
            {
                "model": self.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
                "disable_search": True,
            },
        )

    def request(self, question, key, search, locale=None):
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": question}],
        }
        if not search:
            body["disable_search"] = True
        elif locale:
            body["web_search_options"] = {"user_location": {"country": locale.country}}
        return (
            "https://api.perplexity.ai/chat/completions",
            {"Authorization": f"Bearer {key}"},
            body,
        )

    def parse(self, raw):
        choices = raw.get("choices") or []
        text = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
        results = raw.get("search_results") or []
        if results:
            sources = [Source(r.get("url", ""), r.get("title") or "") for r in results]
        else:
            sources = [Source(url) for url in raw.get("citations") or []]
        return Parsed(text.strip(), sources)


PROVIDERS: tuple[type[Provider], ...] = (OpenAI, Gemini, Anthropic, Perplexity)


def _check_names(names) -> None:
    known = [cls.name for cls in PROVIDERS]
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(f"unknown provider(s): {', '.join(unknown)}; known: {', '.join(known)}")


def all_providers(
    post: PostJson = post_json, models: dict[str, str] | None = None
) -> list[Provider]:
    """Every provider; `models` pins a model id per provider name."""
    models = models or {}
    _check_names(models)
    return [cls(post=post, model=models.get(cls.name)) for cls in PROVIDERS]


def by_name(
    names: list[str], post: PostJson = post_json, models: dict[str, str] | None = None
) -> list[Provider]:
    _check_names([*names, *(models or {})])
    chosen = [p for p in all_providers(post, models) if p.name in names]
    return sorted(chosen, key=lambda p: names.index(p.name))
