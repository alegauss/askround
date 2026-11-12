"""What a round costs: estimated before it runs, capped, and counted after.

A round is dozens of searched calls, and web search is billed apart from tokens, so
'cents to a few dollars a week' is not an answer a person can agree to (law L5: the
person sets the money). Before a round askround prints an estimate from the number of
calls, the tokens a searched answer usually takes and each provider's prices, and
refuses a round above the cap (`--max-cost`, or `ASKROUND_MAX_COST`) before anything is
paid for. After it, each answer's usage as its API reported it (tokens, searches, or
the cost itself where the API gives one) is priced and summed per provider.

The prices below are a table with its date, not a promise: providers change them. The
Anthropic rows are from Anthropic's model table of 2026-11-03; the others are the list
prices last known to the author and must be checked against the providers' pages.
`ASKROUND_PRICES` names a JSON file whose entries replace these, model by model:

    {"models": {"gpt-5": {"input": 1.25, "output": 10.0}},
     "search": {"openai": 0.01}}

Token prices are USD per million tokens; search prices are USD per search.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PRICES_AS_OF = "2026-11-03 (Anthropic); last known list prices for the others: check them"

MODELS: dict[str, dict[str, float]] = {
    # Anthropic, from its model table cached 2026-11-03
    "claude-opus-5-5": {"input": 4.0, "output": 20.0},
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
    "claude-fable-5-2": {"input": 8.0, "output": 40.0},
    # OpenAI, Google and Perplexity: last known list prices, to be checked
    "gpt-5": {"input": 1.25, "output": 10.0},
    "gpt-5-mini": {"input": 0.25, "output": 2.0},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    "sonar": {"input": 1.0, "output": 1.0},
}
# per search (or per grounded request), by provider
SEARCH: dict[str, float] = {
    "openai": 0.01,
    "anthropic": 0.01,
    "gemini": 0.035,
    "perplexity": 0.005,
}
# what a searched answer usually takes, for the estimate: tokens in (search results
# count as input), tokens out (reasoning included), searches
EXPECTED: dict[str, dict[str, float]] = {
    "openai": {"input": 8000, "output": 3000, "searches": 2},
    "anthropic": {"input": 20000, "output": 2000, "searches": 3},
    "gemini": {"input": 1000, "output": 1500, "searches": 1},
    "perplexity": {"input": 1000, "output": 800, "searches": 1},
}
EXTRACTION = {"input": 3000, "output": 800}


def prices() -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    models, search = dict(MODELS), dict(SEARCH)
    path = os.environ.get("ASKROUND_PRICES")
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        models.update(data.get("models") or {})
        search.update(data.get("search") or {})
    return models, search


def _model_price(models: dict, model: str) -> dict[str, float] | None:
    """A dated snapshot ("gpt-5-2025-08-07") is priced as its family ("gpt-5")."""
    if model in models:
        return models[model]
    family = max((m for m in models if model.startswith(m + "-")), key=len, default=None)
    return models[family] if family else None


@dataclass
class Usage:
    input: int = 0
    output: int = 0
    searches: int = 0
    reported_cost: float | None = None  # where the API states the cost itself

    def add(self, other: Usage) -> None:
        self.input += other.input
        self.output += other.output
        self.searches += other.searches
        if other.reported_cost is not None:
            self.reported_cost = (self.reported_cost or 0.0) + other.reported_cost


def usage(provider: str, raw: dict[str, Any]) -> Usage:
    """What one response says it used. A response missing a field counts it as 0."""
    turns = raw.get("turns") or [raw]
    total = Usage()
    for turn in turns:
        u = turn.get("usage") or turn.get("usageMetadata") or {}
        if provider == "openai":
            calls = [i for i in turn.get("output") or [] if i.get("type") == "web_search_call"]
            total.add(Usage(u.get("input_tokens", 0), u.get("output_tokens", 0), len(calls)))
        elif provider == "anthropic":
            searches = (u.get("server_tool_use") or {}).get("web_search_requests", 0)
            total.add(Usage(u.get("input_tokens", 0), u.get("output_tokens", 0), searches))
        elif provider == "gemini":
            out = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
            grounded = any(c.get("groundingMetadata") for c in turn.get("candidates") or [])
            total.add(Usage(u.get("promptTokenCount", 0), out, int(grounded)))
        elif provider == "perplexity":
            cost = (u.get("cost") or {}).get("total_cost")
            searches = 1 if turn.get("search_results") or turn.get("citations") else 0
            total.add(
                Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0), searches, cost)
            )
    return total


def price(provider: str, model: str, used: Usage) -> float | None:
    """USD for what was used; None when the model has no price in the table."""
    if used.reported_cost is not None:
        return used.reported_cost
    models, search = prices()
    rate = _model_price(models, model)
    if rate is None:
        return None
    tokens = used.input * rate["input"] / 1e6 + used.output * rate["output"] / 1e6
    return tokens + used.searches * search.get(provider, 0.0)


@dataclass
class Estimate:
    total: float
    per_provider: dict[str, float] = field(default_factory=dict)
    unpriced: list[str] = field(default_factory=list)  # models with no price


def estimate(providers, calls_per_provider: int, search: bool, extractor=None) -> Estimate:
    """What `calls_per_provider` searched answers from each provider should cost, plus
    reading each with the extractor."""
    models, search_prices = prices()
    est = Estimate(0.0)
    for p in providers:
        rate = _model_price(models, p.model)
        if rate is None:
            est.unpriced.append(f"{p.name}:{p.model}")
            continue
        expect = EXPECTED.get(p.name, {"input": 5000, "output": 2000, "searches": 1})
        one = expect["input"] * rate["input"] / 1e6 + expect["output"] * rate["output"] / 1e6
        if search:
            one += expect["searches"] * search_prices.get(p.name, 0.0)
        est.per_provider[p.name] = one * calls_per_provider
    if extractor is not None:
        rate = _model_price(models, extractor.model)
        answers = calls_per_provider * len(providers)
        if rate is None:
            est.unpriced.append(f"extraction:{extractor.model}")
        else:
            one = (
                EXTRACTION["input"] * rate["input"] / 1e6
                + EXTRACTION["output"] * rate["output"] / 1e6
            )
            est.per_provider["extraction"] = one * answers
    est.total = sum(est.per_provider.values())
    return est


def as_dict(est: Estimate) -> dict:
    return {
        "total": round(est.total, 6),
        "per_provider": {k: round(v, 6) for k, v in est.per_provider.items()},
        "unpriced": est.unpriced,
    }


def describe(est: Estimate) -> str:
    parts = ", ".join(f"{k} ${v:.4f}" for k, v in est.per_provider.items())
    unpriced = f"; no price for {', '.join(est.unpriced)}" if est.unpriced else ""
    return f"estimated cost ${est.total:.4f} ({parts}){unpriced}; prices as of {PRICES_AS_OF}"


def cap(value: float | None) -> float | None:
    """The cap given, else ASKROUND_MAX_COST, else none."""
    if value is not None:
        return value
    env = os.environ.get("ASKROUND_MAX_COST")
    return float(env) if env else None


def actual(round_) -> dict[str, float | None]:
    """USD per provider for the round's answers, and the extraction pass's own calls."""
    spent: dict[str, float | None] = {}
    for r in round_.results:
        if r.answer is None:
            continue
        model = r.answer.served_model or r.answer.model
        cost = price(r.provider, model, usage(r.provider, r.answer.raw))
        if cost is None or spent.get(r.provider, 0.0) is None:
            spent[r.provider] = None
        else:
            spent[r.provider] = spent.get(r.provider, 0.0) + cost
    if round_.extraction_cost is not None:
        spent["extraction"] = round_.extraction_cost
    return spent
