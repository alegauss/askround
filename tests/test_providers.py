"""AR1, AR2: each adapter builds its request, turns web search on or off, and reads the
answer text, the search queries and the cited sources."""

from __future__ import annotations

import pytest
from conftest import ANTHROPIC_RAW, GEMINI_RAW, OPENAI_RAW, PERPLEXITY_RAW, FakePost

from askround.providers import Anthropic, Gemini, OpenAI, Perplexity, Source, by_name


def test_openai_request_and_answer(all_keys):
    post = FakePost()
    answer = OpenAI(post=post).ask("best app?")
    url, headers, body = post.calls[0]
    assert url == "https://api.openai.com/v1/responses"
    assert headers["Authorization"] == "Bearer sk-test"
    assert body["model"] == "gpt-5"
    assert body["input"] == "best app?"
    assert body["tools"] == [{"type": "web_search"}]
    assert answer.text == "OpenAI says Modelado."
    assert answer.raw is OPENAI_RAW
    assert answer.queries == ["photo to 3D app windows"]
    assert answer.sources == [Source("https://modelado.app/", "Modelado")]  # deduplicated


def test_gemini_request_and_answer(all_keys):
    post = FakePost()
    answer = Gemini(post=post).ask("best app?")
    url, headers, body = post.calls[0]
    assert url.endswith("/models/gemini-2.5-flash:generateContent")
    assert headers["x-goog-api-key"] == "g-test"
    assert body["contents"][0]["parts"][0]["text"] == "best app?"
    assert body["tools"] == [{"google_search": {}}]
    assert answer.text == "Gemini says Blender."  # the thought part is left out
    assert answer.raw is GEMINI_RAW
    assert answer.queries == ["free 3d modelling software"]
    assert answer.sources == [Source("https://vertexaisearch.example/r1", "blender.org")]


def test_anthropic_request_and_answer(all_keys):
    post = FakePost()
    answer = Anthropic(post=post).ask("best app?")
    url, headers, body = post.calls[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "a-test"
    assert "anthropic-version" in headers
    assert body["model"] == "claude-opus-5-5"
    assert body["messages"] == [{"role": "user", "content": "best app?"}]
    assert body["tools"][0]["name"] == "web_search"
    assert answer.text == "Claude says Meshy."
    assert answer.raw is ANTHROPIC_RAW
    assert answer.queries == ["image to 3d windows app"]
    assert answer.sources == [Source("https://meshy.ai/", "Meshy")]


def test_anthropic_resumes_a_paused_turn(all_keys):
    paused = {
        "stop_reason": "pause_turn",
        "content": [{"type": "server_tool_use", "name": "web_search", "input": {"query": "first"}}],
    }
    post = FakePost(script={"api.anthropic.com": [paused, ANTHROPIC_RAW]})
    answer = Anthropic(post=post).ask("q")
    assert len(post.calls) == 2
    resent = post.calls[1][2]["messages"]
    assert resent[-1] == {"role": "assistant", "content": paused["content"]}
    assert answer.raw == {"turns": [paused, ANTHROPIC_RAW]}
    assert answer.queries == ["first", "image to 3d windows app"]
    assert answer.text == "Claude says Meshy."


def test_perplexity_request_and_answer(all_keys):
    post = FakePost()
    answer = Perplexity(post=post).ask("best app?")
    url, headers, body = post.calls[0]
    assert url == "https://api.perplexity.ai/chat/completions"
    assert headers["Authorization"] == "Bearer p-test"
    assert body["model"] == "sonar"
    assert "disable_search" not in body
    assert answer.text == "Perplexity says Tripo."
    assert answer.raw is PERPLEXITY_RAW
    assert answer.sources == [Source("https://tripo3d.ai/", "Tripo")]


def test_perplexity_falls_back_to_citations():
    raw = {"choices": [{"message": {"content": "x"}}], "citations": ["https://a.example/"]}
    assert Perplexity().parse(raw).sources == [Source("https://a.example/")]


@pytest.mark.parametrize(
    ("cls", "absent"),
    [(OpenAI, "tools"), (Gemini, "tools"), (Anthropic, "tools")],
)
def test_search_off_sends_no_tool(all_keys, cls, absent):
    post = FakePost()
    answer = cls(post=post).ask("q", search=False)
    assert absent not in post.calls[0][2]
    assert answer.search is False


def test_search_off_on_perplexity_disables_search(all_keys):
    post = FakePost()
    Perplexity(post=post).ask("q", search=False)
    assert post.calls[0][2]["disable_search"] is True


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
