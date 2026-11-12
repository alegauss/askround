"""AR1, AR2, AR4, AR5: a round asks several providers, several times each, and keeps
their answers, what produced them, search queries and sources on disk, with how often
each product was named."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from conftest import GEMINI_RAW, OPENAI_RAW, FakePost

from askround.providers import Answer, all_providers, by_name
from askround.round import Result, Round, frequency, run_round, save_round, slug, summary

NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=timezone.utc)


def test_round_keeps_every_answer(all_keys):
    round_ = run_round("best app?", all_providers(post=FakePost()), now=NOW, runs=1)
    assert [r.provider for r in round_.results] == [
        "openai",
        "gemini",
        "anthropic",
        "perplexity",
    ]
    assert all(r.ok for r in round_.results)
    assert round_.search is True


def test_each_provider_runs_three_times_by_default(all_keys):
    post = FakePost()
    round_ = run_round("q", by_name(["openai", "gemini"], post=post), now=NOW)
    assert round_.runs == 3
    assert [(r.provider, r.run) for r in round_.results] == [
        ("openai", 1),
        ("openai", 2),
        ("openai", 3),
        ("gemini", 1),
        ("gemini", 2),
        ("gemini", 3),
    ]
    assert len(post.calls) == 6
    # each run is a fresh conversation: the same single-message request every time
    openai_bodies = [body for url, _, body in post.calls if "openai" in url]
    assert all(body == openai_bodies[0] for body in openai_bodies)


def test_runs_must_be_positive(all_keys):
    with pytest.raises(ValueError, match="at least 1"):
        run_round("q", all_providers(post=FakePost()), runs=0)


def test_one_failure_costs_one_answer(all_keys):
    post = FakePost(fail={"api.anthropic.com"})
    round_ = run_round("q", all_providers(post=post), now=NOW, runs=1)
    by = {r.provider: r for r in round_.results}
    assert by["openai"].ok and by["gemini"].ok
    assert not by["anthropic"].ok
    assert "HTTP 500" in by["anthropic"].error


def test_save_round_writes_summary_and_raw(all_keys, tmp_path):
    post = FakePost(fail={"api.anthropic.com"})
    round_ = run_round("Best 3D app without NVIDIA?", all_providers(post=post), now=NOW, runs=2)
    directory = save_round(round_, tmp_path, [["Modelado"]])
    assert directory == tmp_path / "2026-11-12" / "143005-best-3d-app-without-nvidia"
    data = json.loads((directory / "round.json").read_text(encoding="utf-8"))
    assert data["question"] == "Best 3D app without NVIDIA?"
    assert data["asked_at"] == "2026-11-12T14:30:05+00:00"
    assert data["search"] is True
    assert data["runs"] == 2
    by = {(r["provider"], r["run"]): r for r in data["results"]}
    assert by[("openai", 1)]["text"] == "OpenAI says Modelado."
    assert by[("openai", 2)]["queries"] == ["photo to 3D app windows"]
    assert by[("openai", 1)]["sources"] == [{"url": "https://modelado.app/", "title": "Modelado"}]
    assert by[("anthropic", 1)]["text"] is None
    for run in (1, 2):
        raw = json.loads((directory / f"openai-{run}.json").read_text(encoding="utf-8"))
        assert raw == OPENAI_RAW
    assert json.loads((directory / "gemini-1.json").read_text(encoding="utf-8")) == GEMINI_RAW
    assert not (directory / "anthropic-1.json").exists()
    product = data["products"][0]
    assert product["product"] == "Modelado"
    openai = next(p for p in product["providers"] if p["provider"] == "openai")
    assert openai == {
        "provider": "openai",
        "locale": None,
        "model": "gpt-5-2025-08-07",
        "runs": 2,
        "named": 2,
        "positions": [None, None],
        "ranked_by": ["text", "text"],
        "evidence": ["", ""],
    }


def test_every_answer_records_what_produced_it(all_keys, tmp_path):
    round_ = run_round("q", all_providers(post=FakePost()), now=NOW, runs=1)
    data = summary(round_)
    by = {r["provider"]: r for r in data["results"]}
    openai = by["openai"]
    assert openai["model"] == "gpt-5"
    assert openai["served_model"] == "gpt-5-2025-08-07"
    assert openai["search_tool"] == [{"type": "web_search"}]
    assert openai["temperature"] is None  # left to the provider's default
    assert openai["locale"] is None
    assert openai["settings"]["include"] == ["web_search_call.action.sources"]
    assert "input" not in openai["settings"]  # the question is not a setting
    assert openai["answered_at"].endswith("+00:00")
    assert openai["run"] == 1
    assert by["gemini"]["served_model"] == "gemini-2.5-flash"
    assert "contents" not in by["gemini"]["settings"]
    assert "messages" not in by["anthropic"]["settings"]
    assert by["anthropic"]["settings"]["max_tokens"] == 16000
    assert by["perplexity"]["served_model"] == "sonar"


def test_frequency_groups_by_served_model():
    a = Answer("openai", "gpt-5", "1. Modelado", {}, served_model="gpt-5-old")
    b = Answer("openai", "gpt-5", "1. Blender", {}, served_model="gpt-5-new")
    round_ = Round(
        "q",
        NOW,
        [
            Result("openai", "gpt-5", 1, answer=a),
            Result("openai", "gpt-5", 2, answer=b),
            Result("gemini", "g", 1, error="HttpError: HTTP 500"),
        ],
        runs=2,
    )
    rows = [(f.provider, f.model, f.share) for f in frequency(round_, ["Modelado"])]
    assert rows == [
        ("openai", "gpt-5-old", "1/1"),
        ("openai", "gpt-5-new", "0/1"),
        ("gemini", "g", "0/0"),
    ]


def _round(texts: dict[str, list[str | None]]) -> Round:
    results = []
    for provider, answers in texts.items():
        for run, text in enumerate(answers, start=1):
            answer = None if text is None else Answer(provider, "m", text, {})
            error = "HttpError: HTTP 500" if text is None else None
            results.append(Result(provider, "m", run, answer=answer, error=error))
    return Round("q", NOW, results, runs=3)


def test_frequency_reports_share_and_positions():
    round_ = _round(
        {
            "openai": [
                "1. Modelado\n2. Blender",
                "1. Blender\n2. Meshy\n3. Modelado",
                "1. Blender\n2. Meshy",
            ],
            "gemini": ["Try modelado, it is free.", None, "- Blender\n- Modelado"],
        }
    )
    table = {f.provider: f for f in frequency(round_, ["Modelado"])}
    assert table["openai"].share == "2/3"
    assert table["openai"].positions == [1, 3, None]
    # the failed run is not counted: 2 answered, both named it
    assert table["gemini"].share == "2/2"
    assert table["gemini"].positions == [None, 2]


def test_summary_without_products_has_no_products_key():
    assert "products" not in summary(_round({"openai": ["x"]}))


def test_round_without_search(all_keys):
    post = FakePost()
    round_ = run_round("q", all_providers(post=post), now=NOW, search=False, runs=1)
    assert round_.search is False
    assert all(r.answer.search is False for r in round_.results)


def test_slug():
    assert slug("Qual o melhor app? (sem NVIDIA)") == "qual-o-melhor-app-sem-nvidia"
    assert slug("???") == "question"
