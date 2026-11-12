"""AR18: a question that names the product it tests is refused before it is paid for,
unless it is marked as a brand question, which is reported apart."""

from __future__ import annotations

import json

from conftest import FakePost

from askround.cli import main
from askround.leading import leads, terms

NAMES = ["Modelado", "alegauss.github.io/modelado", "github.com/alegauss/modelado"]


def test_terms_include_own_hosts_but_not_shared_ones():
    found = terms(NAMES, ["a photo becomes a 3D model"])
    assert "alegauss.github.io" in found
    assert "github.com" not in found
    assert "a photo becomes a 3D model" in found


def test_leads():
    assert leads("Is Modelado any good?", NAMES) == ["Modelado"]
    assert leads("what is on alegauss.github.io?", NAMES) == ["alegauss.github.io"]
    assert leads("an app where a photo becomes a 3D model", NAMES, ["a photo becomes a 3D model"])
    assert leads("best photo to 3D app on GitHub?", NAMES) == []
    assert leads("Modelados3D or Meshroom?", NAMES) == []  # whole words only


def test_ask_refuses_a_leading_question_before_any_call(all_keys, tmp_path, capsys):
    post = FakePost()
    argv = ["ask", "Is Modelado the best photo to 3D app?", "--product", "Modelado"]
    assert main([*argv, "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
    err = capsys.readouterr().err
    assert "names the product it tests (Modelado)" in err
    assert "--brand" in err


def test_a_brand_question_runs_and_is_marked(all_keys, tmp_path, capsys):
    argv = ["ask", "Is Modelado the best photo to 3D app?", "--product", "Modelado", "--brand"]
    code = main(
        [*argv, "--provider", "openai", "--runs", "1", "--json", "--out", str(tmp_path)],
        post=FakePost(),
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["brand"] is True
    assert main(["report", "--out", str(tmp_path)]) == 0
    assert "a brand question: it names the product on purpose" in capsys.readouterr().out


SET = """[product]
name = "Modelado"
places = ["alegauss.github.io/modelado"]
phrases = ["a photo becomes a 3D model"]

[[question]]
text = "Best free photo to 3D app on Windows?"
purpose = "generic"

[[question]]
text = "Is Modelado good for 3D printing?"
purpose = "brand"
brand = true
"""


def test_a_set_keeps_brand_questions_apart(all_keys, tmp_path, capsys):
    path = tmp_path / "p.toml"
    path.write_text(SET, encoding="utf-8")
    argv = ["run", str(path), "--provider", "openai", "--runs", "1"]
    assert main([*argv, "--out", str(tmp_path / "r")], post=FakePost()) == 0
    out = capsys.readouterr().out
    head, _, rest = out.partition("Brand questions name the product on purpose")
    assert "| 1 | Best free photo to 3D app on Windows?" in head
    assert "Is Modelado good" not in head
    assert "| 2 | Is Modelado good for 3D printing?" in rest


def test_a_set_with_an_unmarked_leading_question_is_refused(all_keys, tmp_path, capsys):
    path = tmp_path / "p.toml"
    path.write_text(SET.replace("brand = true\n", ""), encoding="utf-8")
    post = FakePost()
    assert main(["run", str(path), "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
    assert "question 2: the question names the product" in capsys.readouterr().err


def test_discover_refuses_a_leading_seed(all_keys, tmp_path, capsys):
    path = tmp_path / "p.toml"
    path.write_text(SET, encoding="utf-8")
    post = FakePost()
    argv = [
        "discover",
        str(path),
        "--seed",
        "where a photo becomes a 3D model",
        "--out",
        str(tmp_path),
    ]
    assert main(argv, post=post) == 2
    assert post.calls == []
