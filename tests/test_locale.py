"""AR6: a question asked as someone in a country and language, recorded per answer
with what each provider's API ignored."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from conftest import FakePost

from askround.cli import main
from askround.providers import Anthropic, Gemini, Locale, OpenAI, Perplexity, by_name
from askround.round import frequency, run_round, save_round, summary

BR = Locale("BR", "pt-BR")
US = Locale("US", "en-US")
NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=UTC)


def test_parse():
    assert Locale.parse("br:pt-BR") == BR
    assert Locale.parse("US") == Locale("US")
    assert str(BR) == "BR:pt-BR"
    with pytest.raises(ValueError, match="COUNTRY"):
        Locale.parse("Brazil")


def test_openai_and_anthropic_take_the_country(all_keys):
    for cls in (OpenAI, Anthropic):
        post = FakePost()
        answer = cls(post=post).ask("q", locale=BR)
        tool = post.calls[0][2]["tools"][0]
        assert tool["user_location"] == {"type": "approximate", "country": "BR"}
        assert answer.locale == BR
        assert answer.locale_ignored == ["language"]


def test_gemini_takes_the_language(all_keys):
    post = FakePost()
    answer = Gemini(post=post).ask("q", locale=BR)
    body = post.calls[0][2]
    assert body["toolConfig"] == {"retrievalConfig": {"languageCode": "pt-BR"}}
    assert answer.locale_ignored == ["country"]


def test_perplexity_takes_the_country(all_keys):
    post = FakePost()
    answer = Perplexity(post=post).ask("q", locale=BR)
    assert post.calls[0][2]["web_search_options"] == {"user_location": {"country": "BR"}}
    assert answer.locale_ignored == ["language"]


def test_without_search_every_part_is_ignored(all_keys):
    post = FakePost()
    answer = OpenAI(post=post).ask("q", search=False, locale=BR)
    assert "tools" not in post.calls[0][2]
    assert answer.locale_ignored == ["country", "language"]


def test_no_locale_records_none(all_keys):
    answer = OpenAI(post=FakePost()).ask("q")
    assert answer.locale is None
    assert answer.locale_ignored == []


def test_round_in_two_locales_is_compared(all_keys, tmp_path):
    providers = by_name(["openai", "gemini"], post=FakePost())
    round_ = run_round("q", providers, now=NOW, runs=2, locales=[BR, US])
    assert len(round_.results) == 2 * 2 * 2
    rows = [(f.provider, str(f.locale), f.share) for f in frequency(round_, ["Modelado"])]
    assert rows == [
        ("openai", "BR:pt-BR", "2/2"),
        ("openai", "US:en-US", "2/2"),
        ("gemini", "BR:pt-BR", "0/2"),
        ("gemini", "US:en-US", "0/2"),
    ]
    data = summary(round_, [["Modelado"]])
    assert data["locales"] == [
        {"country": "BR", "language": "pt-BR"},
        {"country": "US", "language": "en-US"},
    ]
    first = data["results"][0]
    assert first["locale"] == {"country": "BR", "language": "pt-BR", "ignored": ["language"]}
    directory = save_round(round_, tmp_path, [["Modelado"]])
    assert (directory / "openai-BR-1.json").exists()
    assert (directory / "gemini-US-2.json").exists()


def test_cli_locale_flag(all_keys, tmp_path, capsys):
    argv = ["ask", "q", "--provider", "gemini", "--runs", "1", "--locale", "BR:pt-BR"]
    argv += ["--locale", "US", "--product", "Blender", "--out", str(tmp_path)]
    code = main(argv, post=FakePost())
    out = capsys.readouterr().out
    assert code == 0
    assert "=== gemini (gemini-2.5-flash) [BR:pt-BR, country ignored by the API] ===" in out
    assert "=== gemini (gemini-2.5-flash) [US, country ignored by the API] ===" in out
    assert "gemini      BR:pt-BR 1/1 runs" in out


def test_cli_rejects_a_bad_locale(all_keys, tmp_path):
    with pytest.raises(SystemExit) as exit_:
        main(["ask", "q", "--locale", "Brazil", "--out", str(tmp_path)], post=FakePost())
    assert exit_.value.code == 2


def test_round_json_without_locale(all_keys):
    data = summary(run_round("q", by_name(["openai"], post=FakePost()), now=NOW, runs=1))
    assert data["locales"] == []
    assert data["results"][0]["locale"] is None
    json.dumps(data)  # serialisable
