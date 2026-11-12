"""AR22: a round's cost is estimated before it runs, capped, and counted after."""

from __future__ import annotations

import json

import pytest
from conftest import ANTHROPIC_RAW, GEMINI_RAW, OPENAI_RAW, FakePost

from askround import costs
from askround.cli import main
from askround.providers import by_name


def test_usage_as_each_api_reports_it():
    openai = {**OPENAI_RAW, "usage": {"input_tokens": 9000, "output_tokens": 2000}}
    assert costs.usage("openai", openai) == costs.Usage(9000, 2000, 1)
    anthropic = {
        **ANTHROPIC_RAW,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "server_tool_use": {"web_search_requests": 2},
        },
    }
    assert costs.usage("anthropic", anthropic) == costs.Usage(100, 50, 2)
    gemini = {
        **GEMINI_RAW,
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 20,
            "thoughtsTokenCount": 5,
        },
    }
    assert costs.usage("gemini", gemini) == costs.Usage(10, 25, 1)
    perplexity = {
        "usage": {"prompt_tokens": 5, "completion_tokens": 6, "cost": {"total_cost": 0.007}}
    }
    assert costs.usage("perplexity", perplexity).reported_cost == 0.007


def test_price_of_a_dated_snapshot_and_of_an_unknown_model():
    used = costs.Usage(1_000_000, 1_000_000, 10)
    # gpt-5-2025-08-07 is priced as gpt-5: 1.25 + 10 + 10 searches at 0.01
    assert costs.price("openai", "gpt-5-2025-08-07", used) == pytest.approx(11.35)
    assert costs.price("openai", "mystery-model", used) is None
    assert costs.price("perplexity", "sonar", costs.Usage(reported_cost=0.02)) == 0.02


def test_prices_can_be_overridden(monkeypatch, tmp_path):
    path = tmp_path / "prices.json"
    path.write_text(
        json.dumps({"models": {"gpt-5": {"input": 2.0, "output": 20.0}}}), encoding="utf-8"
    )
    monkeypatch.setenv("ASKROUND_PRICES", str(path))
    assert costs.price("openai", "gpt-5", costs.Usage(1_000_000, 0, 0)) == 2.0


def test_estimate(all_keys):
    providers = by_name(["openai", "gemini"])
    est = costs.estimate(providers, 3, search=True)
    one_openai = 8000 * 1.25 / 1e6 + 3000 * 10 / 1e6 + 2 * 0.01
    assert est.per_provider["openai"] == pytest.approx(3 * one_openai)
    assert est.total == pytest.approx(sum(est.per_provider.values()))
    no_search = costs.estimate(providers, 3, search=False)
    assert no_search.total < est.total


def test_a_round_above_the_cap_is_refused_before_any_call(all_keys, tmp_path, capsys):
    post = FakePost()
    code = main(["ask", "q", "--max-cost", "0.0001", "--out", str(tmp_path)], post=post)
    assert code == 2
    assert post.calls == []
    err = capsys.readouterr().err
    assert "estimated cost $" in err
    assert "above the cap $0.0001" in err


def test_the_cap_can_come_from_the_environment(all_keys, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ASKROUND_MAX_COST", "0.0001")
    post = FakePost()
    assert main(["run", "examples/modelado.toml", "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []


def test_actual_cost_is_reported_per_provider(all_keys, tmp_path, capsys):
    class Billed(FakePost):
        def __call__(self, url, headers, body, timeout):
            raw = super().__call__(url, headers, body, timeout)
            if "openai" in url:
                return {**raw, "usage": {"input_tokens": 1_000_000, "output_tokens": 0}}
            return raw

    argv = ["ask", "q", "--provider", "openai", "--runs", "2", "--json", "--out", str(tmp_path)]
    assert main(argv, post=Billed()) == 0
    data = json.loads(capsys.readouterr().out)
    # two answers, each 1M input tokens at 1.25 and one search at 0.01
    assert data["cost"]["actual"]["openai"] == pytest.approx(2 * 1.26)
    assert data["cost"]["estimate"]["total"] > 0
    assert main(["report", "--out", str(tmp_path)]) == 0
    assert "cost $2.5200" in capsys.readouterr().out
