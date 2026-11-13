"""AR23: an export of rounds another project can load."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime

from askround import export, series
from askround.cli import main
from askround.extract import verify
from askround.providers import Answer, Source
from askround.round import Result, Round, save_round

PRODUCT = ["Modelado", "alegauss.com/modelado"]


def _round(day, texts, question="without NVIDIA?"):
    results = []
    for provider, answers in texts.items():
        for run, text in enumerate(answers, 1):
            answer = Answer(
                provider,
                "m",
                text,
                {},
                sources=[Source("https://alegauss.com/modelado/")],
                answered_at=day,
            )
            names = [line.split(". ", 1)[1] for line in text.splitlines()]
            answer.recommendations = verify(text, [{"name": n, "quote": n} for n in names])
            results.append(Result(provider, "m", run, answer=answer))
    return Round(question, day, results, runs=2)


def _store(tmp_path):
    week1 = datetime(2026, 11, 12, tzinfo=UTC)
    week2 = datetime(2026, 11, 19, tzinfo=UTC)
    save_round(
        _round(week1, {"openai": ["1. Modelado\n2. Modly", "1. Meshroom"]}), tmp_path, [PRODUCT]
    )
    save_round(
        _round(week2, {"openai": ["1. Modly\n2. Modelado", "1. Modelado"]}), tmp_path, [PRODUCT]
    )


def test_rows(tmp_path):
    _store(tmp_path)
    items = export.rows(series.load(tmp_path), "Modelado")
    assert [i["day"] for i in items] == ["2026-11-12", "2026-11-19"]
    first = items[0]
    assert (first["answers"], first["named"], first["frequency"]) == (2, 1, 0.5)
    assert first["best_position"] == 1
    assert first["rivals"] == 2  # Modly and Meshroom
    assert first["cited_pages"] == 1
    assert items[1]["mean_position"] == 1.5
    assert (
        export.rows(series.load(tmp_path), "Modelado", since="2026-11-15")[0]["day"] == "2026-11-19"
    )


def test_csv_loads_back(tmp_path):
    _store(tmp_path)
    text = export.to_csv(export.rows(series.load(tmp_path), "Modelado"))
    loaded = list(csv.DictReader(io.StringIO(text)))
    assert loaded[0]["product"] == "Modelado"
    assert loaded[1]["named"] == "2"
    assert list(loaded[0]) == list(export.FIELDS)


def test_daily_has_the_shape_of_a_daily_json(tmp_path):
    _store(tmp_path)
    data = export.daily(export.rows(series.load(tmp_path), "Modelado"), "modelado")
    day = data["modelado"]["2026-11-19"]["assistants"]
    assert day == {
        "answers": 2,
        "named": 2,
        "best_position": 1,
        "providers": {"openai": {"answers": 2, "named": 2}},
        "frequency": 1.0,
    }


def test_cli_export(tmp_path, capsys):
    _store(tmp_path)
    target = tmp_path / "modelado.csv"
    argv = ["export", "--product", "Modelado", "--file", str(target), "--out", str(tmp_path)]
    assert main(argv) == 0
    assert "exported 2 rows" in capsys.readouterr().out
    assert target.read_text(encoding="utf-8").startswith("day,product,provider")
    argv = ["export", "--product", "Modelado", "--format", "daily", "--out", str(tmp_path)]
    assert main(argv) == 0
    assert "modelado" in json.loads(capsys.readouterr().out)
