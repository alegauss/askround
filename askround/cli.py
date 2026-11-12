"""The `askround` command.

    askround ask "<question>" [--provider NAME ...] [--out DIR] [--json]

Sends the question to every provider whose API key is in the environment (or the
ones named with --provider), prints each answer under its provider's heading, and
saves the round under --out (default `.askround/rounds`, or `ASKROUND_DIR`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from askround import __version__
from askround.providers import all_providers, by_name
from askround.round import Round, run_round, save_round


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="askround", description="Ask several AI assistants the same question."
    )
    parser.add_argument("--version", action="version", version=f"askround {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser("ask", help="send one question to every configured provider")
    ask.add_argument("question")
    ask.add_argument(
        "--provider",
        action="append",
        dest="providers",
        metavar="NAME",
        help="ask only this provider (repeatable)",
    )
    ask.add_argument("--out", type=Path, help="where rounds are saved")
    ask.add_argument("--json", action="store_true", help="print the round as JSON")
    return parser


def main(argv: list[str] | None = None, post=None) -> int:
    args = build_parser().parse_args(argv)
    kwargs = {"post": post} if post is not None else {}
    try:
        providers = by_name(args.providers, **kwargs) if args.providers else all_providers(**kwargs)
    except ValueError as error:
        print(f"askround: {error}", file=sys.stderr)
        return 2
    providers = [p for p in providers if p.configured()]
    if not providers:
        print(
            "askround: no provider has an API key in the environment "
            "(OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY)",
            file=sys.stderr,
        )
        return 2
    out = args.out or Path(os.environ.get("ASKROUND_DIR", ".askround/rounds"))
    round_ = run_round(args.question, providers)
    directory = save_round(round_, out)
    if args.json:
        print(json.dumps(as_json(round_, directory), ensure_ascii=False, indent=2))
    else:
        print(render(round_, directory))
    return 0 if any(r.ok for r in round_.results) else 1


def render(round_: Round, directory: Path) -> str:
    lines = [f"Q: {round_.question}", ""]
    for r in round_.results:
        lines.append(f"=== {r.provider} ({r.model}) ===")
        lines.append(r.answer.text if r.answer else f"[error] {r.error}")
        lines.append("")
    lines.append(f"saved: {directory}")
    return "\n".join(lines)


def as_json(round_: Round, directory: Path) -> dict:
    return {
        "question": round_.question,
        "asked_at": round_.asked_at.isoformat(),
        "saved": str(directory),
        "results": [
            {
                "provider": r.provider,
                "model": r.model,
                "text": r.answer.text if r.answer else None,
                "error": r.error,
            }
            for r in round_.results
        ],
    }
