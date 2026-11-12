"""Shared fixtures: canned provider responses and a fake `post` that records calls.

The canned shapes follow each provider's documented response with web search on, so
the adapters are tested against what a searched answer looks like without paying for
one.
"""

from __future__ import annotations

import pytest

from askround.http import HttpError

OPENAI_RAW = {
    "model": "gpt-5",
    "output": [
        {"type": "reasoning", "summary": []},
        {
            "type": "web_search_call",
            "status": "completed",
            "action": {"type": "search", "query": "photo to 3D app windows"},
        },
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": "OpenAI says Modelado.",
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url": "https://modelado.app/",
                            "title": "Modelado",
                            "start_index": 12,
                            "end_index": 20,
                        },
                        {
                            "type": "url_citation",
                            "url": "https://modelado.app/",
                            "title": "Modelado",
                        },
                    ],
                }
            ],
        },
    ],
}
GEMINI_RAW = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {"text": "hidden reasoning", "thought": True},
                    {"text": "Gemini says "},
                    {"text": "Blender."},
                ]
            },
            "groundingMetadata": {
                "webSearchQueries": ["free 3d modelling software"],
                "groundingChunks": [
                    {"web": {"uri": "https://vertexaisearch.example/r1", "title": "blender.org"}}
                ],
            },
        }
    ]
}
ANTHROPIC_RAW = {
    "stop_reason": "end_turn",
    "content": [
        {
            "type": "server_tool_use",
            "id": "srvtoolu_1",
            "name": "web_search",
            "input": {"query": "image to 3d windows app"},
        },
        {
            "type": "web_search_tool_result",
            "tool_use_id": "srvtoolu_1",
            "content": [
                {"type": "web_search_result", "url": "https://meshy.ai/", "title": "Meshy"},
            ],
        },
        {
            "type": "text",
            "text": "Claude says Meshy.",
            "citations": [
                {
                    "type": "web_search_result_location",
                    "url": "https://meshy.ai/",
                    "title": "Meshy",
                    "cited_text": "Meshy turns images into 3D",
                }
            ],
        },
    ],
}
PERPLEXITY_RAW = {
    "choices": [{"message": {"role": "assistant", "content": "Perplexity says Tripo."}}],
    "citations": ["https://tripo3d.ai/"],
    "search_results": [{"title": "Tripo", "url": "https://tripo3d.ai/", "date": "2026-11-01"}],
}

CANNED = {
    "api.openai.com": OPENAI_RAW,
    "generativelanguage.googleapis.com": GEMINI_RAW,
    "api.anthropic.com": ANTHROPIC_RAW,
    "api.perplexity.ai": PERPLEXITY_RAW,
}

KEY_VARS = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "ANTHROPIC_API_KEY",
    "PERPLEXITY_API_KEY",
)


class FakePost:
    """Answers each host with its canned response; `script` overrides one host with a
    list of responses returned in order."""

    def __init__(self, fail: set[str] | None = None, script: dict[str, list] | None = None):
        self.calls: list[tuple[str, dict, dict]] = []
        self.fail = fail or set()
        self.script = {host: list(answers) for host, answers in (script or {}).items()}

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, body))
        for host, raw in CANNED.items():
            if host in url:
                if host in self.fail:
                    raise HttpError(500, "boom")
                if self.script.get(host):
                    return self.script[host].pop(0)
                return raw
        raise AssertionError(f"unexpected url {url}")


@pytest.fixture
def no_keys(monkeypatch):
    for var in KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    for name in ("OPENAI", "GEMINI", "ANTHROPIC", "PERPLEXITY"):
        monkeypatch.delenv(f"ASKROUND_{name}_MODEL", raising=False)
    monkeypatch.delenv("ASKROUND_DIR", raising=False)


@pytest.fixture
def all_keys(no_keys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-test")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "p-test")
