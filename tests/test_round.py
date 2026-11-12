"""AR1, AR2: a round asks several providers and keeps their answers, search queries
and sources on disk."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from conftest import GEMINI_RAW, OPENAI_RAW, FakePost

from askround.providers import all_providers
from askround.round import run_round, save_round, slug

NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=timezone.utc)


def test_round_keeps_every_answer(all_keys):
    round_ = run_round("best app?", all_providers(post=FakePost()), now=NOW)
    assert [r.provider for r in round_.results] == [
        "openai",
        "gemini",
        "anthropic",
        "perplexity",
    ]
    assert all(r.ok for r in round_.results)
    assert round_.search is True


def test_one_failure_costs_one_answer(all_keys):
    post = FakePost(fail={"api.anthropic.com"})
    round_ = run_round("q", all_providers(post=post), now=NOW)
    by = {r.provider: r for r in round_.results}
    assert by["openai"].ok and by["gemini"].ok
    assert not by["anthropic"].ok
    assert "HTTP 500" in by["anthropic"].error


def test_save_round_writes_summary_and_raw(all_keys, tmp_path):
    post = FakePost(fail={"api.anthropic.com"})
    round_ = run_round("Best 3D app without NVIDIA?", all_providers(post=post), now=NOW)
    directory = save_round(round_, tmp_path)
    assert directory == tmp_path / "2026-11-12" / "143005-best-3d-app-without-nvidia"
    summary = json.loads((directory / "round.json").read_text(encoding="utf-8"))
    assert summary["question"] == "Best 3D app without NVIDIA?"
    assert summary["asked_at"] == "2026-11-12T14:30:05+00:00"
    assert summary["search"] is True
    by = {r["provider"]: r for r in summary["results"]}
    assert by["openai"]["text"] == "OpenAI says Modelado."
    assert by["openai"]["queries"] == ["photo to 3D app windows"]
    assert by["openai"]["sources"] == [{"url": "https://modelado.app/", "title": "Modelado"}]
    assert by["anthropic"]["text"] is None
    assert by["anthropic"]["sources"] == []
    assert json.loads((directory / "openai.json").read_text(encoding="utf-8")) == OPENAI_RAW
    assert json.loads((directory / "gemini.json").read_text(encoding="utf-8")) == GEMINI_RAW
    assert not (directory / "anthropic.json").exists()


def test_round_without_search(all_keys):
    post = FakePost()
    round_ = run_round("q", all_providers(post=post), now=NOW, search=False)
    assert round_.search is False
    assert all(r.answer.search is False for r in round_.results)


def test_slug():
    assert slug("Qual o melhor app? (sem NVIDIA)") == "qual-o-melhor-app-sem-nvidia"
    assert slug("???") == "question"
