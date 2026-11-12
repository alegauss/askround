"""Wire a project to the askround plugin, the way roadkeep wires one (AR38).

`askround install` writes two entries into the project's `.claude/settings.json`: the
marketplace, under `extraKnownMarketplaces`, and the plugin, under `enabledPlugins`.
Committed, they wire every clone: Claude Code offers the marketplace on the first
session and loads the plugin's MCP server, slash commands and skill, with nothing to
install per machine. The plugin carries the package itself (`plugin/src/askround`), so no
`pip install` and no PATH are needed either.

Every other key in the settings is kept as it was. `askround install --check` writes
nothing and exits 1 when an entry is missing or differs, for CI. `--vendor` also commits
a copy of askround for Claude Code on the web, which installs no plugin (below).
"""

from __future__ import annotations

import json
from pathlib import Path

MARKETPLACE = "askround"
PLUGIN = f"askround@{MARKETPLACE}"
SOURCE = {"source": {"source": "github", "repo": "alegauss/askround"}}


def settings_path(project: Path) -> Path:
    return project / ".claude" / "settings.json"


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def missing(settings: dict) -> list[str]:
    """What the settings lack to be wired, one sentence each; empty when wired."""
    gaps = []
    known = settings.get("extraKnownMarketplaces") or {}
    if known.get(MARKETPLACE) != SOURCE:
        gaps.append(f"extraKnownMarketplaces.{MARKETPLACE} is not {json.dumps(SOURCE)}")
    if (settings.get("enabledPlugins") or {}).get(PLUGIN) is not True:
        gaps.append(f"enabledPlugins.{PLUGIN} is not true")
    return gaps


def wire(settings: dict) -> dict:
    """The settings with both entries in place, every other key kept."""
    out = dict(settings)
    out["extraKnownMarketplaces"] = {
        **(settings.get("extraKnownMarketplaces") or {}),
        MARKETPLACE: SOURCE,
    }
    out["enabledPlugins"] = {**(settings.get("enabledPlugins") or {}), PLUGIN: True}
    return out


def install(project: Path, check: bool = False) -> tuple[Path, list[str]]:
    """Wire the project (or, with check, only say what is missing). Returns the settings
    file and what was missing before."""
    path = settings_path(project)
    settings = _read(path)
    gaps = missing(settings)
    if gaps and not check:
        _write(path, wire(settings))
    return path, gaps


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# --- the web: a vendored copy the project commits -------------------------------------
#
# Claude Code on the web installs no marketplace plugin: it reads the repository's own
# files. So `askround install --vendor` copies this package into the project, under
# .claude/ (committed, unlike .askround/ where rounds go), with a launcher, and names it in
# the project's .mcp.json. askround has no dependencies, so the copy is the whole engine.

VENDORED = Path(".claude") / "askround"
LAUNCHER = "run.py"
SERVER = {
    "command": "python",
    "args": [f"${{CLAUDE_PROJECT_DIR:-.}}/{VENDORED.as_posix()}/{LAUNCHER}", "mcp"],
}
_LAUNCHER_TEXT = '''"""askround's MCP server and CLI from the copy beside this file.

Written by `askround install --vendor`; `--vendor --check` says when it is behind.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from askround.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


def _package() -> Path:
    return Path(__file__).resolve().parent


def _sources() -> dict[str, bytes]:
    """The files the copy holds, by path relative to the vendored directory."""
    files = {f"askround/{p.name}": p.read_bytes() for p in sorted(_package().glob("*.py"))}
    files[LAUNCHER] = _LAUNCHER_TEXT.encode("utf-8")
    return files


def vendor_missing(project: Path) -> list[str]:
    """What the project's copy and .mcp.json lack to match this askround."""
    gaps = []
    root = project / VENDORED
    wanted = _sources()
    stale = [
        name
        for name, data in wanted.items()
        if not (root / name).is_file() or (root / name).read_bytes() != data
    ]
    extra = [p for p in (root / "askround").glob("*.py") if f"askround/{p.name}" not in wanted]
    if stale or extra:
        gaps.append(
            f"{VENDORED.as_posix()} differs from askround {_version()} in "
            f"{len(stale) + len(extra)} file(s)"
        )
    servers = _read(project / ".mcp.json").get("mcpServers") or {}
    if servers.get("askround") != SERVER:
        gaps.append(f".mcp.json does not run {VENDORED.as_posix()}/{LAUNCHER} as 'askround'")
    return gaps


def _version() -> str:
    from askround import __version__

    return __version__


def vendor(project: Path, check: bool = False) -> tuple[Path, list[str]]:
    """Copy this askround into the project and name it in .mcp.json (or, with check, only
    say what differs). Files the copy holds that this askround does not are removed."""
    gaps = vendor_missing(project)
    if gaps and not check:
        root = project / VENDORED
        wanted = _sources()
        for old in (root / "askround").glob("*.py"):
            if f"askround/{old.name}" not in wanted:
                old.unlink()
        for name, data in wanted.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(data)
        mcp_json = project / ".mcp.json"
        config = _read(mcp_json)
        config["mcpServers"] = {**(config.get("mcpServers") or {}), "askround": SERVER}
        _write(mcp_json, config)
    return project / VENDORED, gaps
