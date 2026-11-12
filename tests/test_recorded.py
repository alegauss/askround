"""AR29: the adapters and the reading of answers, against responses recorded live.

`tests/fixtures/*-without-nvidia.json` are the raw responses of a live round asked on
2026-11-12 ("What Windows app can turn a single photo into a 3D model without an NVIDIA
GPU (AMD or CPU only)?"), with their response ids replaced; `*.reading.json` is what the
extraction pass read from the OpenAI answer that day. They replace the hand-written
shapes where a real answer says more: real tables, real citations, real usage.
"""

from __future__ import annotations

import json
from pathlib import Path

from askround import costs
from askround.extract import Recommendation, verify
from askround.mention import find, locate
from askround.providers import Answer, Gemini, OpenAI

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_openai_recorded_answer():
    raw = _load("openai-without-nvidia.json")
    provider = OpenAI()
    parsed = provider.parse(raw)
    assert "Modelado" in parsed.text
    assert parsed.sources, "a searched answer cites its pages"
    assert any(
        "alegauss.github.io/modelado" in s.url or "github.com/alegauss/modelado" in s.url
        for s in parsed.sources
    )
    assert parsed.queries, "the web_search_call items carry the queries"
    assert provider.served_model(raw) == "gpt-5-2025-08-07"
    used = costs.usage("openai", raw)
    assert used.input > 0 and used.output > 0 and used.searches >= 1


def test_gemini_recorded_answer():
    raw = _load("gemini-without-nvidia.json")
    provider = Gemini()
    parsed = provider.parse(raw)
    assert parsed.text
    assert parsed.sources, "grounding chunks become sources"
    assert all(s.title for s in parsed.sources), "a redirect is known by the domain in its title"
    assert provider.served_model(raw) == "gemini-2.5-flash"
    assert costs.usage("gemini", raw).searches == 1


def test_the_recorded_reading_ranks_modelado_first():
    raw = _load("openai-without-nvidia.json")
    reading = _load("openai-without-nvidia.reading.json")
    answer = Answer("openai", "gpt-5", OpenAI().parse(raw).text, raw)
    answer.recommendations = [Recommendation(**r) for r in reading["recommendations"]]
    found = locate(answer, ["Modelado"])
    assert (found.named, found.position, found.by) == (True, 1, "extraction")
    # the plain-text reading agrees that it is named
    assert find(answer.text, ["Modelado"]).named


def test_the_recorded_quotes_are_found_in_the_answer():
    raw = _load("openai-without-nvidia.json")
    text = OpenAI().parse(raw).text
    reading = _load("openai-without-nvidia.reading.json")
    checked = verify(
        text, [{"name": r["name"], "quote": r["quote"]} for r in reading["recommendations"]]
    )
    assert [r.verified for r in checked] == [r["verified"] for r in reading["recommendations"]]
