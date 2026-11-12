"""AR1, AR2: `askround ask` returns the answers of several providers, with their
sources, and saves them."""

from __future__ import annotations

import json

from conftest import FakePost

from askround.cli import main


def test_ask_prints_answers_side_by_side(all_keys, tmp_path, capsys):
    code = main(["ask", "best app?", "--out", str(tmp_path)], post=FakePost())
    out = capsys.readouterr().out
    assert code == 0
    assert "=== openai (gpt-5) ===" in out
    assert "OpenAI says Modelado." in out
    assert "Gemini says Blender." in out
    assert "Claude says Meshy." in out
    assert "Perplexity says Tripo." in out
    assert "  - Modelado <https://modelado.app/>" in out
    assert "web search off" not in out
    assert "saved:" in out
    assert len(list(tmp_path.glob("*/*/round.json"))) == 1


def test_no_search_flag(all_keys, tmp_path, capsys):
    post = FakePost()
    code = main(["ask", "q", "--no-search", "--out", str(tmp_path)], post=post)
    out = capsys.readouterr().out
    assert code == 0
    assert "(web search off)" in out
    assert all("tools" not in body for _, _, body in post.calls)


def test_only_providers_with_keys_are_asked(no_keys, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    post = FakePost()
    code = main(["ask", "q", "--out", str(tmp_path), "--json"], post=post)
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert [r["provider"] for r in data["results"]] == ["openai", "gemini"]
    assert not any("anthropic" in url for url, _, _ in post.calls)


def test_provider_flag_narrows(all_keys, tmp_path, capsys):
    code = main(
        ["ask", "q", "--provider", "gemini", "--out", str(tmp_path), "--json"], post=FakePost()
    )
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert [r["provider"] for r in data["results"]] == ["gemini"]


def test_no_keys_is_an_error(no_keys, tmp_path, capsys):
    code = main(["ask", "q", "--out", str(tmp_path)], post=FakePost())
    assert code == 2
    assert "no provider has an API key" in capsys.readouterr().err


def test_all_failing_exits_one(all_keys, tmp_path, capsys):
    post = FakePost(
        fail={
            "api.openai.com",
            "generativelanguage.googleapis.com",
            "api.anthropic.com",
            "api.perplexity.ai",
        }
    )
    code = main(["ask", "q", "--out", str(tmp_path)], post=post)
    assert code == 1
    assert "[error]" in capsys.readouterr().out


def test_out_defaults_to_askround_dir(all_keys, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ASKROUND_DIR", str(tmp_path / "rounds"))
    assert main(["ask", "q"], post=FakePost()) == 0
    assert list((tmp_path / "rounds").glob("*/*/round.json"))
