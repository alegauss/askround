"""AR20: every round is kept as a series, and a product's share is read per week."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from conftest import FakePost

from askround import series
from askround.cli import main
from askround.providers import Answer
from askround.round import Result, Round, save_round


def _round(day: datetime, texts: dict[str, list[str]], question: str = "q") -> Round:
    results = []
    for provider, answers in texts.items():
        for run, text in enumerate(answers, 1):
            answer = Answer(provider, "m", text, {}, answered_at=day)
            results.append(Result(provider, "m", run, answer=answer))
    return Round(question, day, results, runs=2)


def test_saved_rounds_append_one_row_per_answer(tmp_path):
    day = datetime(2026, 11, 12, 10, tzinfo=UTC)
    round_ = _round(day, {"openai": ["1. Modelado", "1. Modly"]})
    save_round(round_, tmp_path, [["Modelado"]])
    rows = series.load(tmp_path)
    assert len(rows) == 2
    first = rows[0]
    assert first["week"] == "2026-W46"
    assert first["day"] == "2026-11-12"
    assert first["provider"] == "openai"
    assert first["products"] == {"Modelado": {"named": True, "position": 1, "cited": []}}
    assert first["round"].endswith("/round.json")
    assert rows[1]["products"]["Modelado"]["named"] is False


def test_frequency_per_week_per_provider(tmp_path):
    weeks = [
        (datetime(2026, 11, 12, tzinfo=UTC), ["1. Modelado", "1. Modly"], ["1. Modly", "1. Modly"]),
        (
            datetime(2026, 11, 19, tzinfo=UTC),
            ["1. Modelado", "1. Modelado"],
            ["2. Modelado", "1. Modly"],
        ),
    ]
    for day, openai, gemini in weeks:
        save_round(_round(day, {"openai": openai, "gemini": gemini}), tmp_path, [["Modelado"]])
    table = series.frequency(series.load(tmp_path), "Modelado")
    assert table == {
        "2026-W46": {"openai": {"named": 1, "answers": 2}, "gemini": {"named": 0, "answers": 2}},
        "2026-W47": {"openai": {"named": 2, "answers": 2}, "gemini": {"named": 1, "answers": 2}},
    }


def test_brand_and_other_questions_are_filtered(tmp_path):
    day = datetime(2026, 11, 12, tzinfo=UTC)
    brand = _round(day, {"openai": ["Modelado is fine"]}, "is Modelado good?")
    brand.brand = True
    save_round(brand, tmp_path, [["Modelado"]])
    save_round(_round(day, {"openai": ["1. Modelado"]}, "without NVIDIA"), tmp_path, [["Modelado"]])
    rows = series.load(tmp_path)
    assert series.frequency(rows, "Modelado")["2026-W46"]["openai"]["answers"] == 1
    assert series.frequency(rows, "Modelado", question="nvidia")["2026-W46"]["openai"]["named"] == 1
    assert series.frequency(rows, "Modelado", question="printing") == {}


def test_rebuild_writes_the_series_again_from_the_rounds(tmp_path):
    save_round(
        _round(datetime(2026, 11, 12, tzinfo=UTC), {"openai": ["1. Modelado"]}),
        tmp_path,
        [["Modelado"]],
    )
    (tmp_path / series.FILE).unlink()
    assert series.rebuild(tmp_path) == 1
    assert series.load(tmp_path)[0]["products"]["Modelado"]["position"] == 1


def test_rebuild_reads_rounds_from_older_versions_and_names_broken_ones(tmp_path):
    old = tmp_path / "2026-11-12" / "100000-q"
    old.mkdir(parents=True)
    # the shape AR1 wrote: no run, no served model, no locale
    (old / "round.json").write_text(
        json.dumps(
            {
                "question": "q",
                "asked_at": "2026-11-12T10:00:00+00:00",
                "results": [
                    {"provider": "openai", "model": "gpt-5", "text": "1. Modelado", "error": None}
                ],
            }
        ),
        encoding="utf-8",
    )
    broken = tmp_path / "2026-11-12" / "110000-x"
    broken.mkdir(parents=True)
    (broken / "round.json").write_text("{}", encoding="utf-8")
    skipped: list[str] = []
    assert series.rebuild(tmp_path, skipped) == 1
    assert series.load(tmp_path)[0]["run"] == 1
    assert len(skipped) == 1 and "110000-x" in skipped[0]


def test_cli_series(all_keys, tmp_path, capsys):
    argv = ["ask", "q", "--provider", "openai", "--runs", "2", "--product", "Modelado"]
    main([*argv, "--out", str(tmp_path)], post=FakePost())
    capsys.readouterr()
    assert main(["series", "--product", "Modelado", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "| week | openai |" in out
    assert "| 2/2 |" in out
    assert (
        main(["series", "--product", "Modelado", "--by", "day", "--json", "--out", str(tmp_path)])
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert (data["product"], data["by"]) == ("Modelado", "day")
    assert list(data["periods"].values())[0]["openai"] == {"named": 2, "answers": 2}


def test_cli_series_needs_a_product(tmp_path, capsys):
    assert main(["series", "--out", str(tmp_path)]) == 2
