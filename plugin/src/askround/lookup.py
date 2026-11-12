"""Does a product an answer recommends exist? Looked up, not taken on the answer's word.

An answer can recommend an app that does not exist, and a rival table built from answers
inherits what the model invented. The other mistake is as costly: on 12/11/2026 a
search by hand failed to find 'Presidium Shape Studio' and 'MeshForge3D' and took them
for inventions, and both turned out to be real (a PyPI package, and a TripoSR-based
Windows app on GitHub). So nothing is called invented on one failed search. Each name
is looked up, cheapest first:

1. GitHub repository search (free; `GITHUB_TOKEN` raises its rate limit): a repository
   whose name is the product's name, with at least 10 stars, is enough to call it
   found, with the repository as the evidence.
2. A web search through one provider (OpenAI, Anthropic or Gemini, one paid call per
   name): the model searches and says found, ambiguous or not found, with the page.
   Its own word is checked too (law L4): a "found" whose page is not among the pages
   its search returned is downgraded to ambiguous.

A name neither lookup could settle is "unknown", never "found".
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit

from askround import mention
from askround.http import ATTEMPTS, PostJson, post_json, with_retries
from askround.providers import Anthropic, Gemini, OpenAI

STATUSES = ("found", "ambiguous", "not_found")
MIN_STARS = 10

PROMPT = """Search the web to check whether a real software product, app or service named "{name}" exists and can be obtained today{context}.

Answer "found" only if you find its official website, source repository or app store page. Answer "ambiguous" if the name only matches something different (another kind of product, a person, a company with no such product) or the evidence is unclear. Answer "not_found" if nothing turns up. Give the address of the official page you found (empty if none) and one sentence of evidence."""

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": list(STATUSES)},
        "url": {"type": "string"},
        "evidence": {"type": "string"},
    },
    "required": ["status", "url", "evidence"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Verdict:
    name: str
    status: str  # found, ambiguous, not_found or unknown
    url: str = ""
    evidence: str = ""
    via: str = ""  # "github", "web:<provider>", or "" when nothing could look


def _squash(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", mention.core(name).lower())


def github(name: str, post: PostJson) -> Verdict | None:
    """A repository named like the product, or None when GitHub could not say."""
    wanted = _squash(name)
    if not wanted:
        return None
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "askround"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    query = quote(f"{mention.core(name)} in:name")
    url = f"https://api.github.com/search/repositories?q={query}&per_page=5"
    try:
        data = post(url, headers, None, 30.0)
    except Exception:  # noqa: BLE001 - a rate limit or outage leaves it to the web lookup
        return None
    for repo in data.get("items") or []:
        stars = repo.get("stargazers_count", 0)
        # a repository merely named like it proves little: a stray one is easy to find
        if _squash(repo.get("name", "")) == wanted and stars >= MIN_STARS:
            evidence = f"repository {repo.get('full_name')} ({stars} stars)"
            return Verdict(name, "found", repo.get("html_url", ""), evidence, "github")
    return None


class WebLookup:
    """One searched call per name, on one provider."""

    provider: type
    default_model: str = ""

    def __init__(self, post: PostJson = post_json, timeout: float = 180.0):
        self._post = with_retries(post, ATTEMPTS)
        self._source = self.provider(post=post)
        self.timeout = timeout

    @property
    def name(self) -> str:
        return self.provider.name

    def configured(self) -> bool:
        return self._source.configured()

    def check(self, name: str, context: str = "") -> Verdict:
        key = self._source.api_key()
        if key is None:
            raise RuntimeError(f"{self.name}: no API key for the web lookup")
        hint = f" (an answer recommended it for: {context})" if context else ""
        url, headers, body = self.request(PROMPT.format(name=name, context=hint), key)
        raw = self._post(url, headers, body, self.timeout)
        parsed = self._source.parse(raw)
        data = _json(parsed.text)
        status = data.get("status") if data.get("status") in STATUSES else "unknown"
        page = str(data.get("url") or "").strip()
        evidence = str(data.get("evidence") or "").strip()
        searched = {_host(s.url) for s in parsed.sources} | {
            s.title.lower() for s in parsed.sources if "." in s.title
        }
        if status == "found" and _host(page) not in searched:
            status = "ambiguous"
            evidence = f"{evidence} (its page was not among the pages the search returned)"
        return Verdict(name, status, page, evidence, f"web:{self.name}")

    def request(self, prompt: str, key: str) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError


class OpenAIWeb(WebLookup):
    provider = OpenAI

    def request(self, prompt, key):
        return (
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {key}"},
            {
                "model": os.environ.get("ASKROUND_LOOKUP_MODEL") or "gpt-5-mini",
                "input": prompt,
                "tools": [{"type": "web_search"}],
                "include": ["web_search_call.action.sources"],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "verdict",
                        "schema": VERDICT_SCHEMA,
                        "strict": True,
                    }
                },
            },
        )


class AnthropicWeb(WebLookup):
    provider = Anthropic

    def request(self, prompt, key):
        return (
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2026-10-21"},
            {
                "model": os.environ.get("ASKROUND_LOOKUP_MODEL") or "claude-haiku-5-5",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}],
                "tools": [{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
                "output_config": {"format": {"type": "json_schema", "schema": VERDICT_SCHEMA}},
            },
        )


class GeminiWeb(WebLookup):
    """Grounding and a response schema cannot be combined, so the JSON is asked for in
    the prompt and read from the text."""

    provider = Gemini

    def request(self, prompt, key):
        model = os.environ.get("ASKROUND_LOOKUP_MODEL") or "gemini-2.5-flash"
        ask = (
            prompt
            + '\n\nReply with only a JSON object: {"status": ..., "url": ..., "evidence": ...}'
        )
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            {"x-goog-api-key": key},
            {
                "contents": [{"role": "user", "parts": [{"text": ask}]}],
                "tools": [{"google_search": {}}],
            },
        )


WEB_LOOKUPS: tuple[type[WebLookup], ...] = (OpenAIWeb, AnthropicWeb, GeminiWeb)


def web_lookup(post: PostJson = post_json) -> WebLookup | None:
    for cls in WEB_LOOKUPS:
        lookup = cls(post=post)
        if lookup.configured():
            return lookup
    return None


def _json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _host(url: str) -> str:
    host = urlsplit(url if "//" in url else f"https://{url}").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def check(
    names: list[str],
    context: str = "",
    post: PostJson = post_json,
    web: WebLookup | None = None,
    parallel: int = 4,
) -> list[Verdict]:
    """A verdict per name, in order: GitHub first, then the web lookup if one is given."""

    def one(name: str) -> Verdict:
        found = github(name, post)
        if found:
            return found
        if web is None:
            return Verdict(
                name, "unknown", evidence="no repository of that name; no web lookup ran"
            )
        try:
            return web.check(name, context)
        except Exception as error:  # noqa: BLE001 - an unsettled name stays unknown
            return Verdict(name, "unknown", evidence=f"{type(error).__name__}: {error}"[:200])

    with ThreadPoolExecutor(max_workers=max(1, min(len(names), parallel))) as pool:
        return list(pool.map(one, names))
