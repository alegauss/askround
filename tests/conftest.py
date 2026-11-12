"""Shared fixtures: canned provider responses and a fake `post` that records calls."""

from __future__ import annotations

import pytest

from askround.http import HttpError

OPENAI_RAW = {
    "model": "gpt-5",
    "output": [
        {"type": "reasoning", "summary": []},
        {
            "type": "message",
            "content": [{"type": "output_text", "text": "OpenAI says Modelado."}],
        },
    ],
}
GEMINI_RAW = {
    "candidates": [{"content": {"parts": [{"text": "Gemini says "}, {"text": "Blender."}]}}]
}
ANTHROPIC_RAW = {"content": [{"type": "text", "text": "Claude says Meshy."}]}

CANNED = {
    "api.openai.com": OPENAI_RAW,
    "generativelanguage.googleapis.com": GEMINI_RAW,
    "api.anthropic.com": ANTHROPIC_RAW,
}

KEY_VARS = ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY")


class FakePost:
    def __init__(self, fail: set[str] | None = None):
        self.calls: list[tuple[str, dict, dict]] = []
        self.fail = fail or set()

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, body))
        for host, raw in CANNED.items():
            if host in url:
                if host in self.fail:
                    raise HttpError(500, "boom")
                return raw
        raise AssertionError(f"unexpected url {url}")


@pytest.fixture
def no_keys(monkeypatch):
    for var in KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    for name in ("OPENAI", "GEMINI", "ANTHROPIC"):
        monkeypatch.delenv(f"ASKROUND_{name}_MODEL", raising=False)
    monkeypatch.delenv("ASKROUND_DIR", raising=False)


@pytest.fixture
def all_keys(no_keys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-test")
