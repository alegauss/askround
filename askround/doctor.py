"""`askround doctor`: which providers can run here, without printing a key.

For each provider askround knows it reports the variable its key was read from (the
name, never the value), the model it would use, how it searches, and the result of
the cheapest call that proves the key and the model work: a free model lookup on
OpenAI, Gemini and Anthropic, and a one-token call with search off on Perplexity,
which has no lookup.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from askround.http import HttpError
from askround.providers import Provider


@dataclass
class Status:
    provider: str
    model: str
    search_tool: str
    key_var: str | None
    checked: bool
    ok: bool
    detail: str

    @property
    def can_run(self) -> bool:
        return self.key_var is not None and (self.ok or not self.checked)


def diagnose(providers: list[Provider], check: bool = True) -> list[Status]:
    def one(provider: Provider) -> Status:
        key_var = provider.key_var()
        base = {
            "provider": provider.name,
            "model": provider.model,
            "search_tool": provider.search_tool,
            "key_var": key_var,
        }
        if key_var is None:
            vars_ = " or ".join(provider.key_vars)
            return Status(**base, checked=False, ok=False, detail=f"no key: set {vars_}")
        if not check:
            return Status(**base, checked=False, ok=False, detail="key set, not checked")
        try:
            provider.check()
        except Exception as error:  # noqa: BLE001 - every failure is a diagnosis
            return Status(**base, checked=True, ok=False, detail=_explain(error, provider))
        return Status(**base, checked=True, ok=True, detail="ok")

    with ThreadPoolExecutor(max_workers=max(1, len(providers))) as pool:
        return list(pool.map(one, providers))


def _explain(error: Exception, provider: Provider) -> str:
    if isinstance(error, HttpError):
        if error.status in (401, 403):
            return f"key rejected (HTTP {error.status})"
        if error.status == 404:
            return f"model {provider.model} not found (HTTP 404)"
        return f"HTTP {error.status}"
    return f"{type(error).__name__}: {error}"
