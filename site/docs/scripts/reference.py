"""Write the reference the docs render, from the package itself (AR42).

The MCP tools with their input schemas, and every CLI command with its arguments, read off
`askround.mcp.TOOLS` and `askround.cli.build_parser()` and written to
`src/data/reference.generated.json`. A page typed by hand would be a second statement of
both, and the stale one the first time a flag is added. Run by `npm run prebuild`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "plugin" / "src"))

from askround import __version__  # noqa: E402
from askround.cli import build_parser  # noqa: E402
from askround.mcp import TOOLS  # noqa: E402


def _argument(action: argparse.Action) -> dict:
    return {
        "name": ", ".join(action.option_strings) or action.metavar or action.dest,
        "positional": not action.option_strings,
        "help": (action.help or "").replace("%(default)s", str(action.default)),
        "choices": [str(c) for c in action.choices] if action.choices else [],
    }


def commands() -> list[dict]:
    parser = build_parser()
    (sub,) = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    helps = {choice.dest: choice.help for choice in sub._choices_actions}
    found = []
    for name, command in sub.choices.items():
        arguments = [
            _argument(a)
            for a in command._actions
            if not isinstance(a, argparse._HelpAction) and a.help != argparse.SUPPRESS
        ]
        found.append({"name": name, "help": helps.get(name, ""), "arguments": arguments})
    return found


def tools() -> list[dict]:
    found = []
    for tool in TOOLS:
        schema = tool["inputSchema"]
        required = set(schema.get("required", []))
        params = [
            {
                "name": key,
                "type": _type(spec),
                "required": key in required,
                "description": spec.get("description", ""),
            }
            for key, spec in schema.get("properties", {}).items()
        ]
        found.append({"name": tool["name"], "description": tool["description"], "params": params})
    return found


def _type(spec: dict) -> str:
    if spec.get("type") == "array":
        items = spec.get("items", {})
        inner = " | ".join(items["enum"]) if "enum" in items else items.get("type", "")
        return f"array of {inner}"
    return str(spec.get("type", ""))


if __name__ == "__main__":
    out = HERE.parent / "src" / "data" / "reference.generated.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": __version__, "tools": tools(), "commands": commands()}
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"reference: {len(data['tools'])} tools, {len(data['commands'])} commands -> {out}")
