"""AR9: the products a round's answers recommend, aggregated with counts and ranks."""

from __future__ import annotations

from datetime import datetime, timezone

from askround.extract import verify
from askround.providers import Answer
from askround.rivals import key, rivals
from askround.round import Result, Round, summary

NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=timezone.utc)

# SYNTHETIC answers in the shape the 12/11/2026 notes describe for the general question
GENERAL = "1. Modly (open-source desktop app)\n2. Trellis Studio\n3. Meshroom\n"
WITHOUT_NVIDIA = "1. Modelado - runs on the CPU\n2. Modly\n"


def _answer(provider, text, names):
    answer = Answer(provider, "m", text, {})
    answer.recommendations = verify(text, [{"name": n, "quote": n} for n in names])
    return answer


def _round(*answers):
    results = [Result(a.provider, "m", i, answer=a) for i, a in enumerate(answers, 1)]
    return Round("q", NOW, results, runs=len(results))


def test_key_normalises_names():
    assert key("Modly (open-source desktop app)") == "modly"
    assert key("**Modly**") == "modly"
    assert key("Reallusion CC — faces") == "reallusion cc"
    assert key("Modelado: runs on the CPU") == "modelado"
    assert key("Stable-Fast 3D") == "stable-fast 3d"


def test_rivals_counted_with_ranks_and_providers():
    round_ = _round(
        _answer(
            "openai", GENERAL, ["Modly (open-source desktop app)", "Trellis Studio", "Meshroom"]
        ),
        _answer("gemini", GENERAL, ["Modly", "Meshroom"]),
        _answer("openai", WITHOUT_NVIDIA, ["Modelado", "Modly"]),
    )
    found = rivals(round_, [["Modelado"]])
    assert found.read == 3
    top = found.rivals[0]
    assert top.name == "Modly (open-source desktop app)".split(" (")[0]
    assert top.answers == 3
    assert top.ranks == [1, 1, 2]
    assert top.providers == {"openai": 2, "gemini": 1}
    names = [r.name for r in found.rivals]
    assert names == ["Modly", "Meshroom", "Trellis Studio"]
    assert "Modelado" not in names  # the product is not its own rival


def test_a_name_with_added_notes_still_stands():
    text = "1. Modly\n2. Meshroom\n"
    round_ = _round(_answer("openai", text, ["Modly (opensource desktop app)", "Meshroom"]))
    # the quotes are the names here, so make them verifiable against the text
    assert [r.name for r in rivals(round_).rivals] == ["Modly", "Meshroom"]


def test_invented_products_are_left_out():
    round_ = _round(_answer("openai", GENERAL, ["Nowhere Shape Studio", "Modly"]))
    assert [r.name for r in rivals(round_).rivals] == ["Modly"]


def test_without_extraction_there_is_no_list():
    round_ = _round(Answer("openai", "m", GENERAL, {}))
    found = rivals(round_)
    assert found.rivals == []
    assert "--extract" in found.missing


def test_round_json_carries_the_rivals():
    round_ = _round(_answer("openai", GENERAL, ["Modly", "Meshroom"]))
    data = summary(round_, [["Meshroom"]])
    assert data["rivals"]["read"] == 1
    assert data["rivals"]["missing"] is None
    assert data["rivals"]["products"] == [
        {
            "name": "Modly",
            "answers": 1,
            "ranks": [1],
            "providers": {"openai": 1},
            "reason": "Modly",
            "exists": None,
        }
    ]
