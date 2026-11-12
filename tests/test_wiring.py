"""AR38: the plugin runs askround with nothing installed, and `askround install` wires a
project's settings so every clone gets it."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from askround import jobs, mcp, wiring
from askround.cli import main

ROOT = Path(__file__).parent.parent
PLUGIN = ROOT / "plugin"


def test_install_writes_the_marketplace_and_the_plugin_and_keeps_the_rest(tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"enabledPlugins": {"roadkeep@alegauss": True}, "x": 1}))
    assert main(["install", str(tmp_path), "--check"]) == 1
    assert main(["install", str(tmp_path)]) == 0
    written = json.loads(settings.read_text())
    assert written["x"] == 1
    assert written["enabledPlugins"] == {"roadkeep@alegauss": True, "askround@askround": True}
    assert written["extraKnownMarketplaces"]["askround"] == wiring.SOURCE
    assert main(["install", str(tmp_path), "--check"]) == 0


def test_install_creates_the_settings_and_check_writes_nothing(tmp_path):
    assert main(["install", str(tmp_path), "--check"]) == 1
    assert not (tmp_path / ".claude").exists()
    assert main(["install", str(tmp_path)]) == 0
    assert wiring.missing(json.loads(wiring.settings_path(tmp_path).read_text())) == []


def test_install_refuses_settings_that_are_not_an_object(tmp_path):
    (tmp_path / ".claude").mkdir()
    wiring.settings_path(tmp_path).write_text("[]")
    assert main(["install", str(tmp_path)]) == 2


def test_the_marketplace_names_the_plugin_install_wires():
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert market["name"] == wiring.MARKETPLACE
    assert [p["name"] for p in market["plugins"]] == ["askround"]
    assert (ROOT / market["plugins"][0]["source"]).resolve() == PLUGIN.resolve()


def test_the_plugin_carries_the_package_and_its_launcher_runs_with_nothing_installed(tmp_path):
    config = json.loads((PLUGIN / ".claude-plugin" / "mcp.json").read_text(encoding="utf-8"))
    args = config["mcpServers"]["askround"]["args"]
    script = Path(args[0].replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN)))
    assert script.is_file() and args[1:] == ["mcp"]
    assert (PLUGIN / "src" / "askround" / "cli.py").is_file()
    # a bare interpreter, from another directory, with no PYTHONPATH: only the launcher's
    # own path can find the package
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    done = subprocess.run(
        [sys.executable, "-S", str(script), "explain", "question.leading"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    assert "question.leading" in done.stdout or done.stdout.strip()


def test_a_job_imports_the_copy_that_started_it():
    env = jobs._environment()
    first = env["PYTHONPATH"].split(os.pathsep)[0]
    assert Path(first) == Path(jobs.__file__).resolve().parents[1]


def test_vendor_commits_a_copy_the_web_runs_and_check_sees_it_go_stale(tmp_path):
    assert main(["install", str(tmp_path), "--vendor", "--check"]) == 1
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {"roadkeep": {"command": "x"}}}))
    assert main(["install", str(tmp_path), "--vendor"]) == 0
    servers = json.loads((tmp_path / ".mcp.json").read_text())["mcpServers"]
    assert set(servers) == {"roadkeep", "askround"}
    assert main(["install", str(tmp_path), "--vendor", "--check"]) == 0
    # the web runs it from the project with nothing installed
    launcher = servers["askround"]["args"][0].replace("${CLAUDE_PROJECT_DIR:-.}", str(tmp_path))
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    done = subprocess.run(
        [sys.executable, "-S", launcher, "explain", "question.leading"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    # a file changed, or one this askround no longer has: stale until install runs again
    copied = tmp_path / wiring.VENDORED / "askround"
    (copied / "cli.py").write_text("# edited\n")
    (copied / "gone.py").write_text("")
    assert main(["install", str(tmp_path), "--vendor", "--check"]) == 1
    assert main(["install", str(tmp_path), "--vendor"]) == 0
    assert not (copied / "gone.py").exists()
    assert wiring.vendor_missing(tmp_path) == []


def test_the_schemas_carry_the_project_files_and_the_person_budget(tmp_path, monkeypatch):
    (tmp_path / "sets").mkdir()
    (tmp_path / "sets" / "app.toml").write_text(
        '[product]\nname = "App"\n[[question]]\ntext = "which app?"\n', encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text("[product]\n", encoding="utf-8")
    (tmp_path / "broken.toml").write_text("[product\n", encoding="utf-8")
    config = Path(os.environ["ASKROUND_CONFIG"])
    config.write_text("[budget]\nday = 1.5\nmonth = 10\n", encoding="utf-8")
    listed = {t["name"]: t for t in mcp.tools(str(tmp_path / "rounds"), tmp_path)}
    run_file = listed["askround_run"]["inputSchema"]["properties"]["file"]["description"]
    assert run_file.endswith("in this project: sets/app.toml (1 questions)")
    cost = listed["askround_ask"]["inputSchema"]["properties"]["max_cost"]["description"]
    assert "$1.50 a day ($0.00 spent today)" in cost and "$10.00 a month" in cost


def test_every_command_names_tools_the_server_has():
    tools = {t["name"] for t in mcp.tools()}
    commands = sorted((PLUGIN / "commands").glob("*.md"))
    assert [c.stem for c in commands] == ["ask", "diff", "report", "run"]
    for command in commands:
        text = command.read_text(encoding="utf-8")
        allowed = re.search(r"^allowed-tools: (.+)$", text, re.M).group(1).split(", ")
        named = {a.rsplit("__", 1)[1] for a in allowed}
        assert named <= tools, (command.name, named - tools)
