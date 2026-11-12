"""AR3: `askround doctor` says which providers can run, and never prints a key."""

from __future__ import annotations

import json

from conftest import FakePost

from askround.cli import main
from askround.doctor import diagnose
from askround.providers import all_providers

SECRETS = ("sk-test", "g-test", "a-test", "p-test")


def test_all_keys_valid(all_keys, capsys):
    post = FakePost()
    code = main(["doctor"], post=post)
    out = capsys.readouterr().out
    assert code == 0
    assert "can run: openai, gemini, anthropic, perplexity" in out
    assert "OPENAI_API_KEY" in out
    assert not any(secret in out for secret in SECRETS)


def test_checks_are_free_lookups_except_perplexity(all_keys):
    post = FakePost()
    diagnose(all_providers(post=post))
    by_host = {url.split("/")[2]: (url, body) for url, _, body in post.calls}
    assert by_host["api.openai.com"] == ("https://api.openai.com/v1/models/gpt-5", None)
    assert by_host["api.anthropic.com"][1] is None
    assert by_host["generativelanguage.googleapis.com"][1] is None
    perplexity = by_host["api.perplexity.ai"][1]
    assert perplexity["max_tokens"] == 1 and perplexity["disable_search"] is True


def test_absent_key_is_reported_without_a_call(no_keys, monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    post = FakePost()
    code = main(["doctor", "--json"], post=post)
    data = {s["provider"]: s for s in json.loads(capsys.readouterr().out)}
    assert code == 0
    assert data["openai"]["can_run"] is True
    assert data["gemini"]["key_var"] is None
    assert data["gemini"]["detail"] == "no key: set GEMINI_API_KEY or GOOGLE_API_KEY"
    assert data["gemini"]["can_run"] is False
    assert [url for url, _, _ in post.calls] == ["https://api.openai.com/v1/models/gpt-5"]


def test_invalid_key_and_missing_model(all_keys, capsys):
    post = FakePost(fail={"api.openai.com": 401, "api.anthropic.com": 404})
    code = main(["doctor", "--json"], post=post)
    out = capsys.readouterr().out
    data = {s["provider"]: s for s in json.loads(out)}
    assert code == 0
    assert data["openai"]["detail"] == "key rejected (HTTP 401)"
    assert data["openai"]["can_run"] is False
    assert data["anthropic"]["detail"] == "model claude-opus-5-5 not found (HTTP 404)"
    # the error body echoes the headers in this fake; doctor must not print it
    assert not any(secret in out for secret in SECRETS)


def test_no_provider_can_run_exits_two(no_keys, capsys):
    code = main(["doctor"], post=FakePost())
    assert code == 2
    assert "no provider can run" in capsys.readouterr().out


def test_no_check_makes_no_call(all_keys, capsys):
    post = FakePost()
    code = main(["doctor", "--no-check", "--provider", "gemini"], post=post)
    out = capsys.readouterr().out
    assert code == 0
    assert post.calls == []
    assert "key set, not checked" in out
    assert "GEMINI_API_KEY" in out
