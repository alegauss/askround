"""AR19: a question carrying personal data stops before any call, naming what it found.

Every address, number and name below is made up for the test."""

from __future__ import annotations

import pytest
from conftest import FakePost

from askround.cli import main
from askround.private import scan


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("mail me at jane.doe@example.com about it", "an email address"),
        ("call +55 11 91234-5678", "a phone number"),
        ("call (11) 3456-7890 today", "a phone number"),
        ("my CPF is 123.456.789-09", "a CPF"),
        ("the server at 192.168.10.20 is slow", "an IP address"),
        ("key sk-abcdefghijklmnopqrstuvwxyz", "an API key"),
    ],
)
def test_scan_finds(text, kind):
    assert kind in scan(text, terms=[])


@pytest.mark.parametrize(
    "text",
    [
        "best free photo to 3D app on Windows 10 (1903+) or 11?",
        "does modelado.app work offline?",
        "TripoSR vs Hunyuan3D 2.1 for a 3D print of 120 mm",
        "Qual app de Windows transforma uma foto em modelo 3D usando só a CPU?",
        "a model from 2026-11-12",
    ],
)
def test_scan_leaves_ordinary_questions_alone(text):
    assert scan(text, terms=[]) == []


def test_private_terms_from_the_environment_and_a_file(monkeypatch, tmp_path):
    names = tmp_path / "private.txt"
    names.write_text("# people\nZelda Fictitious\n", encoding="utf-8")
    monkeypatch.setenv("ASKROUND_PRIVATE", "Quentin Madeup")
    monkeypatch.setenv("ASKROUND_PRIVATE_FILE", str(names))
    assert scan("what would Quentin Madeup use?") == ["the private term 'Quentin Madeup'"]
    assert scan("ask zelda fictitious") == ["the private term 'Zelda Fictitious'"]


def test_ask_stops_before_any_call_and_says_why(all_keys, tmp_path, capsys):
    post = FakePost()
    question = "Which app does jane.doe@example.com use for photo to 3D?"
    assert main(["ask", question, "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
    err = capsys.readouterr().err
    assert "the question carries an email address" in err
    assert "refused before anything was sent" in err


def test_a_set_with_personal_data_is_refused(all_keys, tmp_path, capsys):
    path = tmp_path / "p.toml"
    path.write_text(
        '[product]\nname = "X"\n[[question]]\ntext = "ok?"\n'
        '[[question]]\ntext = "call +55 11 91234-5678 about photo to 3D"\n',
        encoding="utf-8",
    )
    post = FakePost()
    assert main(["run", str(path), "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
    assert "question 2 carries a phone number" in capsys.readouterr().err


def test_lookup_is_refused_too(all_keys, capsys):
    post = FakePost()
    assert main(["lookup", "Modly", "--context", "for jane.doe@example.com"], post=post) == 2
    assert post.calls == []
