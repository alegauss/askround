"""AR35: a round runs as a job; the agent reads it later, and an interrupted job keeps
what it finished."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from conftest import FakePost

from askround import jobs, mcp
from askround.cli import main


def test_estimate_only_asks_nothing(all_keys, tmp_path, capsys):
    post = FakePost()
    assert main(["ask", "q", "--estimate-only", "--out", str(tmp_path)], post=post) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["schema"] == "askround/estimate@1"
    assert data["estimate"]["total"] > 0
    assert post.calls == []
    assert not list(tmp_path.glob("*/*/round.json"))


def test_a_job_records_each_answer_as_it_lands(all_keys, tmp_path, capsys):
    directory = tmp_path / "jobs" / "j1"
    directory.mkdir(parents=True)
    argv = ["ask", "q", "--provider", "openai", "--provider", "gemini", "--runs", "2", "--json"]
    code = main([*argv, "--job", str(directory), "--out", str(tmp_path)], post=FakePost())
    assert code == 0
    (directory / "result.json").write_text(capsys.readouterr().out, encoding="utf-8")
    progress = (directory / "progress.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(progress) == 4
    assert sorted(p.name for p in (directory / "answers").glob("*.json")) == [
        "gemini-1.json",
        "gemini-2.json",
        "openai-1.json",
        "openai-2.json",
    ]
    assert (directory / "exit").read_text(encoding="utf-8") == "0"
    found = jobs.status("j1", tmp_path)
    assert (found["state"], found["answered"], found["failed"]) == ("done", 4, 0)
    assert found["result"]["schema"] == "askround/round@1"


def test_an_interrupted_job_keeps_what_it_finished(tmp_path):
    directory = tmp_path / "jobs" / "j2" / "answers"
    directory.mkdir(parents=True)
    (directory / "openai-1.json").write_text('{"text": "1. Modelado"}', encoding="utf-8")
    (directory.parent / "progress.jsonl").write_text(
        '{"answer": "openai#1", "ok": true, "error": null}\n', encoding="utf-8"
    )
    found = jobs.status("j2", tmp_path)
    assert found["state"] == "interrupted"
    assert found["answered"] == 1
    assert found["kept"] == ["openai-1.json"]


def test_a_refused_job_says_why(all_keys, tmp_path, capsys):
    directory = tmp_path / "jobs" / "j3"
    directory.mkdir(parents=True)
    argv = ["ask", "jane@example.com?", "--json", "--job", str(directory), "--out", str(tmp_path)]
    assert main(argv, post=FakePost()) == 2
    (directory / "stderr.log").write_text(capsys.readouterr().err, encoding="utf-8")
    found = jobs.status("j3", tmp_path)
    assert found["state"] == "refused"
    assert "question.personal-data" in found["stderr"]


def test_start_runs_in_its_own_process(tmp_path):
    # a stand-in for askround: waits a little, then finishes the job it was given
    stub = (
        "import sys, time, pathlib; a = sys.argv; d = pathlib.Path(a[a.index('--job') + 1]);"
        "time.sleep(0.5); print('{\"ok\": true}'); (d / 'exit').write_text('0')"
    )
    job = jobs.start(["ask", "q"], tmp_path, command=[sys.executable, "-c", stub])
    assert jobs.status(job, tmp_path)["state"] == "running"
    argv = json.loads((tmp_path / "jobs" / job / "argv.json").read_text(encoding="utf-8"))
    assert argv[-4:] == ["--job", str(tmp_path / "jobs" / job), "--out", str(tmp_path)]
    deadline = time.time() + 20
    while jobs.status(job, tmp_path)["state"] == "running" and time.time() < deadline:
        time.sleep(0.1)
    found = jobs.status(job, tmp_path)
    assert found["state"] == "done"
    assert found["result"] == {"ok": True}


def test_an_agent_starts_a_round_keeps_working_and_reads_it_later(all_keys, tmp_path, monkeypatch):
    started = {}

    def fake_start(argv, out, command=None):
        """Run the job in this process, as the real one would in its own."""
        job = "j-agent"
        directory = Path(out) / "jobs" / job
        directory.mkdir(parents=True)
        started["argv"] = argv
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main([*argv, "--json", "--job", str(directory), "--out", str(out)], post=FakePost())
        (directory / "result.json").write_text(buffer.getvalue(), encoding="utf-8")
        return job

    monkeypatch.setattr(jobs, "start", fake_start)
    arguments = {"question": "q", "providers": ["openai"], "runs": 2, "background": True}
    reply = mcp.call("askround_ask", arguments, str(tmp_path), FakePost())
    assert reply["isError"] is False
    started_reply = json.loads(reply["content"][0]["text"])
    assert started_reply["state"] == "running"
    assert started_reply["estimate"]["total"] > 0
    assert "--approve" not in started["argv"]
    reply = mcp.call("askround_job", {"job": started_reply["job"]}, str(tmp_path))
    found = json.loads(reply["content"][0]["text"])
    assert found["state"] == "done"
    assert found["result"]["schema"] == "askround/brief@1"
    assert found["result"]["answers"] == 2


def test_a_background_start_is_refused_like_any_round(all_keys, tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "start", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    reply = mcp.call(
        "askround_ask", {"question": "mail jane@example.com", "background": True}, str(tmp_path)
    )
    assert reply["isError"] is True
    assert "question.personal-data" in reply["content"][0]["text"]
