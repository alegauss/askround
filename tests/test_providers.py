"""AR1: each provider adapter builds its request and reads the answer text."""

from __future__ import annotations

import pytest
from conftest import ANTHROPIC_RAW, GEMINI_RAW, OPENAI_RAW, FakePost

from askround.providers import Anthropic, Gemini, OpenAI, by_name


def test_openai_request_and_text(all_keys):
    post = FakePost()
    answer = OpenAI(post=post).ask("best app?")
    url, headers, body = post.calls[0]
    assert url == "https://api.openai.com/v1/responses"
    assert headers["Authorization"] == "Bearer sk-test"
    assert body == {"model": "gpt-5", "input": "best app?"}
    assert answer.text == "OpenAI says Modelado."
    assert answer.raw is OPENAI_RAW


def test_gemini_request_and_text(all_keys):
    post = FakePost()
    answer = Gemini(post=post).ask("best app?")
    url, headers, body = post.calls[0]
    assert url.endswith("/models/gemini-2.5-flash:generateContent")
    assert headers["x-goog-api-key"] == "g-test"
    assert body["contents"][0]["parts"][0]["text"] == "best app?"
    assert answer.text == "Gemini says Blender."
    assert answer.raw is GEMINI_RAW


def test_anthropic_request_and_text(all_keys):
    post = FakePost()
    answer = Anthropic(post=post).ask("best app?")
    url, headers, body = post.calls[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "a-test"
    assert "anthropic-version" in headers
    assert body["model"] == "claude-opus-5-5"
    assert body["messages"] == [{"role": "user", "content": "best app?"}]
    assert answer.text == "Claude says Meshy."
    assert answer.raw is ANTHROPIC_RAW


def test_model_overridden_by_environment(all_keys, monkeypatch):
    monkeypatch.setenv("ASKROUND_OPENAI_MODEL", "gpt-other")
    post = FakePost()
    answer = OpenAI(post=post).ask("q")
    assert post.calls[0][2]["model"] == "gpt-other"
    assert answer.model == "gpt-other"


def test_gemini_falls_back_to_google_api_key(no_keys, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "google")
    assert Gemini().api_key() == "google"


def test_missing_key_raises_without_calling(no_keys):
    post = FakePost()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAI(post=post).ask("q")
    assert post.calls == []


def test_by_name_rejects_unknown():
    with pytest.raises(ValueError, match="unknown provider"):
        by_name(["openai", "nope"])
