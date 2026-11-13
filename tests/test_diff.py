"""AR21: two stored rounds compared, every change named."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from askround import diff
from askround.cli import main
from askround.extract import verify, verify_claims
from askround.providers import Answer, Source
from askround.round import Result, Round, save_round

PRODUCT = ["Modelado", "alegauss.com/modelado", "github.com/alegauss/modelado"]


def _round(day, text, recs, claims, sources):
    answer = Answer("openai", "m", text, {}, sources=[Source(s) for s in sources], answered_at=day)
    answer.recommendations = verify(text, [{"name": n, "quote": n} for n in recs])
    answer.claims = verify_claims(text, claims)
    return Round("photo to 3D without NVIDIA?", day, [Result("openai", "m", 1, answer=answer)])


def _store(tmp_path):
    week1 = _round(
        datetime(2026, 11, 12, tzinfo=UTC),
        "1. Modelado (CPU only: Check build)\n2. Meshroom",
        ["Modelado", "Meshroom"],
        [
            {
                "product": "Modelado",
                "attribute": "CPU only",
                "value": "Check build",
                "quote": "Check build",
            }
        ],
        ["https://github.com/alegauss/modelado"],
    )
    week2 = _round(
        datetime(2026, 11, 19, tzinfo=UTC),
        "1. Modly\n2. Modelado (CPU only: Yes)",
        ["Modly", "Modelado"],
        [
            {
                "product": "Modelado",
                "attribute": "CPU only",
                "value": "Yes",
                "quote": "CPU only: Yes",
            }
        ],
        ["https://alegauss.com/modelado/"],
    )
    a = save_round(week1, tmp_path, [PRODUCT])
    b = save_round(week2, tmp_path, [PRODUCT])
    return a / "round.json", b / "round.json"


def test_every_change_is_named(tmp_path):
    old, new = _store(tmp_path)
    found = {(c.kind, c.detail) for c in diff.compare(old, new)}
    assert ("share", "1/1, best #1 -> 1/1, best #2") in found
    assert ("rival", "new: Modly") in found
    assert ("rival", "gone: Meshroom") in found
    assert ("cited", "new: https://alegauss.com/modelado") in found
    assert ("cited", "gone: https://github.com/alegauss/modelado") in found
    assert ("claims", "new: CPU only: Yes") in found
    assert ("claims", "gone: CPU only: Check build") in found


def test_latest_pair_finds_the_same_question(tmp_path):
    old, new = _store(tmp_path)
    assert diff.latest_pair(tmp_path) == (old, new)


def test_cli_diff_latest_two(tmp_path, capsys):
    _store(tmp_path)
    assert main(["diff", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# What changed")
    assert "| openai | rival | new: Modly |" in out
    assert main(["diff", "--out", str(tmp_path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {"question", "provider", "kind", "detail"} <= set(data["changes"][0])


def test_one_side_without_extraction_is_not_comparable(tmp_path):
    old, new = _store(tmp_path)
    data = json.loads(old.read_text(encoding="utf-8"))
    for item in data["results"]:
        item["recommendations"] = None
        item["claims"] = None
    old.write_text(json.dumps(data), encoding="utf-8")
    kinds = {(c.kind, c.detail) for c in diff.compare(old, new)}
    assert ("rival", "not comparable: --extract ran on one side only") in kinds
    assert not any(detail.startswith("new: Modly") for _, detail in kinds)


def test_nothing_to_compare(tmp_path, capsys):
    assert main(["diff", "--out", str(tmp_path)]) == 2
    assert "no round under" in capsys.readouterr().err
