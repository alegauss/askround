"""Rounds as jobs: a long round runs in its own process, and is read when it is done.

A round of dozens of searched calls takes minutes. An MCP tool that blocks that long
freezes the agent and can time out, throwing away answers already paid for. So a round
can start as a job: the command line runs in a process of its own with `--job <dir>`,
and the job's directory is the whole state:

    <out>/jobs/<id>/
        argv.json        what was run
        progress.jsonl   one line per answer, as each lands (provider, run, ok, error)
        answers/         each finished answer, written the moment it lands
        result.json      the command's JSON, when it finished
        exit             its exit code (0, 1, 2 or 3), when it finished
        stderr.log       what it said on the way

Because each answer is written as it lands, an interrupted job (the process killed, the
machine restarted) keeps every answer it finished. A job is read by its id: running,
done (with its result), refused, failed, or interrupted (with what it finished).
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path

from askround.provenance import answer_id

# the processes this server started, to tell running from interrupted
_RUNNING: dict[str, subprocess.Popen] = {}


def jobs_dir(out: Path) -> Path:
    return out / "jobs"


def new_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)


COMMAND = [sys.executable, "-m", "askround"]


def _environment() -> dict[str, str]:
    """The job imports the copy of askround that started it: the plugin runs askround from
    its own source tree with nothing installed, and `-m askround` alone would not find it."""
    here = str(Path(__file__).resolve().parents[1])
    paths = [here, *filter(None, os.environ.get("PYTHONPATH", "").split(os.pathsep))]
    return {**os.environ, "PYTHONPATH": os.pathsep.join(paths)}


def start(argv: list[str], out: Path, command: list[str] | None = None) -> str:
    """Run `askround <argv> --json --job <dir> --out <out>` in its own process."""
    job = new_id()
    directory = jobs_dir(out) / job
    directory.mkdir(parents=True)
    full = [*argv, "--json", "--job", str(directory), "--out", str(out)]
    (directory / "argv.json").write_text(json.dumps(full), encoding="utf-8")
    process = subprocess.Popen(
        [*(command or COMMAND), *full],
        stdout=(directory / "result.json").open("w", encoding="utf-8"),
        stderr=(directory / "stderr.log").open("w", encoding="utf-8"),
        stdin=subprocess.DEVNULL,
        env=_environment(),
    )
    _RUNNING[job] = process
    return job


class Recorder:
    """Called by the round as each answer lands; writes it at once (thread-safe)."""

    def __init__(self, directory: Path):
        self.directory = directory
        (directory / "answers").mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def __call__(self, result) -> None:
        line = {
            "answer": answer_id(result),
            "ok": result.ok,
            "error": result.error,
            "at": datetime.now(UTC).isoformat(),
        }
        with self._lock:
            if result.answer is not None:
                kept = {
                    "answer": line["answer"],
                    "model": result.answer.served_model or result.answer.model,
                    "text": result.answer.text,
                    "sources": [{"url": s.url, "title": s.title} for s in result.answer.sources],
                }
                name = line["answer"].replace("#", "-").replace("@", "-")
                (self.directory / "answers" / f"{name}.json").write_text(
                    json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            with (self.directory / "progress.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line) + "\n")


def finish(directory: Path, code: int) -> None:
    (directory / "exit").write_text(str(code), encoding="utf-8")


def status(job: str, out: Path) -> dict:
    """What a job is doing or did."""
    directory = jobs_dir(out) / job
    if not directory.is_dir():
        raise FileNotFoundError(f"no job {job} under {jobs_dir(out)}")
    progress = []
    path = directory / "progress.jsonl"
    if path.is_file():
        progress = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line
        ]
    done = {
        "job": job,
        "answered": sum(p["ok"] for p in progress),
        "failed": sum(not p["ok"] for p in progress),
    }
    exit_file = directory / "exit"
    if exit_file.is_file():
        code = int(exit_file.read_text(encoding="utf-8").strip() or 1)
        state = {0: "done", 3: "done", 1: "failed", 2: "refused"}.get(code, "failed")
        found = {**done, "state": state, "exit": code}
        result = directory / "result.json"
        if state == "done" and result.is_file() and result.stat().st_size:
            found["result"] = json.loads(result.read_text(encoding="utf-8"))
        if state in ("failed", "refused"):
            found["stderr"] = (directory / "stderr.log").read_text(encoding="utf-8")[-2000:]
        return found
    process = _RUNNING.get(job)
    if process is not None and process.poll() is None:
        return {**done, "state": "running"}
    # no exit code, and no live process: it was interrupted; what it finished is kept
    kept = sorted(p.name for p in (directory / "answers").glob("*.json"))
    return {**done, "state": "interrupted", "kept": kept, "answers_dir": str(directory / "answers")}
