"""Wire a project to the askround plugin, the way roadkeep wires one (AR38).

`askround install` writes two entries into the project's `.claude/settings.json`: the
marketplace, under `extraKnownMarketplaces`, and the plugin, under `enabledPlugins`.
Committed, they wire every clone: Claude Code offers the marketplace on the first
session and loads the plugin's MCP server, slash commands and skill, with nothing to
install per machine. The plugin carries the package itself (`plugin/src/askround`), so no
`pip install` and no PATH are needed either.

Every other key in the settings is kept as it was. `askround install --check` writes
nothing and exits 1 when an entry is missing or differs, for CI.
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(wire(settings), indent=2) + "\n", encoding="utf-8")
    return path, gaps
