"""AR16: a product file's questions run as one prompt set, again and again."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import FakePost

from askround.cli import main
from askround.product import Question, load
from askround.providers import Locale
from askround.report import build_set, find_round, set_markdown

EXAMPLE = Path(__file__).parent.parent / "examples" / "modelado.toml"


def test_the_four_questions_of_12_11_live_in_the_example_set():
    product = load(EXAMPLE)
    assert product.name == "Modelado"
    assert [q.purpose for q in product.questions] == [
        "generic",
        "constraint",
        "use case",
        "language",
    ]
    assert product.questions[3].locale == Locale("BR", "pt-BR")
    assert product.facts[0].attribute == "Runs without an NVIDIA GPU"


def test_a_question_needs_a_text_and_sane_runs(tmp_path):
    path = tmp_path / "p.toml"
    path.write_text('[product]\nname = "X"\n[[question]]\npurpose = "generic"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="question 1 needs a text"):
        load(path)
    path.write_text('[product]\nname = "X"\n[[question]]\ntext = "q"\nruns = 0\n', encoding="utf-8")
    with pytest.raises(ValueError, match="runs must be"):
        load(path)
    path.write_text('[product]\nname = "X"\n[[question]]\ntext = "q"\nruns = 2\n', encoding="utf-8")
    assert load(path).questions == [Question("q", "", None, 2)]


def test_run_asks_every_question_as_one_set(all_keys, tmp_path, capsys):
    post = FakePost()
    argv = ["run", str(EXAMPLE), "--provider", "openai", "--provider", "gemini", "--runs", "1"]
    code = main([*argv, "--out", str(tmp_path)], post=post)
    out = capsys.readouterr().out
    assert code == 0
    # four questions, two providers, one run each
    asked = [body for url, _, body in post.calls if body]
    assert len(asked) == 8
    pt = [
        b
        for b in asked
        if "CPU" in json.dumps(b, ensure_ascii=False)
        and "Qual" in json.dumps(b, ensure_ascii=False)
    ]
    assert pt and pt[0].get("tools") is not None
    sets = list(tmp_path.glob("*/*/set.json"))
    assert len(sets) == 1
    index = json.loads(sets[0].read_text(encoding="utf-8"))
    assert [q["n"] for q in index["questions"]] == [1, 2, 3, 4]
    assert index["questions"][3]["locale"] == "BR:pt-BR"
    assert all((sets[0].parent / q["round"]).is_file() for q in index["questions"])
    assert out.startswith("# Modelado: prompt set")
    assert "| # | question | purpose | openai | gemini |" in out
    first = "| 1 | What is a free offline app to turn a photo into a 3D model on Windows? |"
    assert f"{first} generic | 1/1 -" in out
    assert "## 2. What app can turn a photo" in out


def test_report_reads_the_latest_set(all_keys, tmp_path, capsys):
    main(
        ["run", str(EXAMPLE), "--provider", "openai", "--runs", "1", "--out", str(tmp_path)],
        post=FakePost(),
    )
    capsys.readouterr()
    path = find_round(None, tmp_path)
    assert path.name == "set.json"
    assert main(["report", "--out", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("# Modelado: prompt set")
    data = build_set(path)
    assert len(data["questions"]) == 4
    assert "| 4 | Qual app de Windows" in set_markdown(data)


def test_a_file_without_questions_is_refused(all_keys, tmp_path, capsys):
    path = tmp_path / "p.toml"
    path.write_text('[product]\nname = "X"\n', encoding="utf-8")
    post = FakePost()
    assert main(["run", str(path), "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
    assert "no [[question]]" in capsys.readouterr().err
