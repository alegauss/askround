"""The `askround` command.

    askround ask "<question>" [--provider NAME ...] [--model PROVIDER=MODEL ...]
                 [--runs N] [--product NAME[,ALIAS...]] [--locale COUNTRY[:LANG] ...]
                 [--no-search] [--out DIR] [--json]
    askround doctor [--provider NAME ...] [--model PROVIDER=MODEL ...] [--no-check] [--json]

`ask` sends the question to every provider whose API key is in the environment (or the
ones named with --provider), --runs times each (default 3), with web search on unless
--no-search, prints each answer under its provider's heading with the sources it
cited, then for each --product the share of runs that named it and its positions, and
saves the round under --out (default `.askround/rounds`, or `ASKROUND_DIR`).

`doctor` says which providers can run here: key variable (never the value), model,
search tool and a free check call. It exits 2 when no provider can run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from askround import __version__
from askround.doctor import Status, diagnose
from askround.providers import Answer, Locale, all_providers, by_name
from askround.round import DEFAULT_RUNS, Round, frequency, run_round, save_round, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="askround", description="Ask several AI assistants the same question."
    )
    parser.add_argument("--version", action="version", version=f"askround {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--provider",
        action="append",
        dest="providers",
        metavar="NAME",
        help="only this provider (repeatable)",
    )
    common.add_argument(
        "--model",
        action="append",
        dest="models",
        type=_pin,
        metavar="PROVIDER=MODEL",
        help="pin the model one provider uses (repeatable)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser(
        "ask", parents=[common], help="send one question to every configured provider"
    )
    ask.add_argument("question")
    ask.add_argument(
        "--no-search",
        dest="search",
        action="store_false",
        help="ask without web search, to compare with a searched round",
    )
    ask.add_argument(
        "--runs",
        type=_positive,
        default=DEFAULT_RUNS,
        help=f"times each provider is asked, in fresh conversations (default {DEFAULT_RUNS})",
    )
    ask.add_argument(
        "--product",
        action="append",
        dest="products",
        type=_names,
        metavar="NAME[,ALIAS...]",
        help="report how often this product is named and where (repeatable)",
    )
    ask.add_argument(
        "--locale",
        action="append",
        dest="locales",
        type=_locale,
        metavar="COUNTRY[:LANGUAGE]",
        help="ask as someone in this country, e.g. BR:pt-BR; repeat to compare (each "
        "locale is a full set of runs)",
    )
    ask.add_argument("--out", type=Path, help="where rounds are saved")
    ask.add_argument("--json", action="store_true", help="print the round as JSON")
    doctor = commands.add_parser(
        "doctor", parents=[common], help="say which providers can run here"
    )
    doctor.add_argument(
        "--no-check", dest="check", action="store_false", help="make no network call"
    )
    doctor.add_argument("--json", action="store_true", help="print the report as JSON")
    return parser


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _pin(value: str) -> tuple[str, str]:
    provider, sep, model = value.partition("=")
    if not sep or not provider.strip() or not model.strip():
        raise argparse.ArgumentTypeError("expected PROVIDER=MODEL, e.g. openai=gpt-5")
    return provider.strip(), model.strip()


def _locale(value: str) -> Locale:
    try:
        return Locale.parse(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def _names(value: str) -> list[str]:
    names = [n.strip() for n in value.split(",") if n.strip()]
    if not names:
        raise argparse.ArgumentTypeError("a product needs a name")
    return names


def main(argv: list[str] | None = None, post=None) -> int:
    args = build_parser().parse_args(argv)
    kwargs = {"post": post} if post is not None else {}
    kwargs["models"] = dict(args.models or [])
    try:
        providers = by_name(args.providers, **kwargs) if args.providers else all_providers(**kwargs)
    except ValueError as error:
        print(f"askround: {error}", file=sys.stderr)
        return 2
    if args.command == "doctor":
        return run_doctor(providers, args.check, args.json)
    providers = [p for p in providers if p.configured()]
    if not providers:
        print(
            "askround: no provider has an API key in the environment "
            "(OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, PERPLEXITY_API_KEY)",
            file=sys.stderr,
        )
        return 2
    out = args.out or Path(os.environ.get("ASKROUND_DIR", ".askround/rounds"))
    products = args.products or []
    round_ = run_round(
        args.question, providers, search=args.search, runs=args.runs, locales=args.locales
    )
    directory = save_round(round_, out, products)
    if args.json:
        data = {**summary(round_, products), "saved": str(directory)}
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render(round_, directory, products))
    return 0 if any(r.ok for r in round_.results) else 1


def run_doctor(providers, check: bool, as_json_: bool) -> int:
    statuses = diagnose(providers, check=check)
    if as_json_:
        print(json.dumps([_status_json(s) for s in statuses], indent=2))
    else:
        print(render_doctor(statuses))
    return 0 if any(s.can_run for s in statuses) else 2


def _status_json(s: Status) -> dict:
    return {
        "provider": s.provider,
        "model": s.model,
        "search_tool": s.search_tool,
        "key_var": s.key_var,
        "checked": s.checked,
        "ok": s.ok,
        "can_run": s.can_run,
        "detail": s.detail,
    }


def render_doctor(statuses: list[Status]) -> str:
    rows = [("provider", "key", "model", "search", "status")]
    for s in statuses:
        mark = "ok" if s.ok else ("-" if not s.checked else "FAIL")
        status = s.detail if s.detail == "ok" else f"{mark}: {s.detail}"
        rows.append((s.provider, s.key_var or "-", s.model, s.search_tool, status))
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    lines = [
        "  ".join(cell.ljust(w) for cell, w in zip(row[:4], widths, strict=True)) + "  " + row[4]
        for row in rows
    ]
    can = [s.provider for s in statuses if s.can_run]
    lines.append("")
    lines.append(f"can run: {', '.join(can)}" if can else "no provider can run")
    return "\n".join(lines)


def render(round_: Round, directory: Path, products: list[list[str]] | None = None) -> str:
    lines = [f"Q: {round_.question}", ""]
    if not round_.search:
        lines[0] += "  (web search off)"
    for r in round_.results:
        run = f", run {r.run}/{round_.runs}" if round_.runs > 1 else ""
        lines.append(f"=== {r.provider} ({_model(r)}{run}){_place(r)} ===")
        lines.extend(_answer_lines(r.answer) if r.answer else [f"[error] {r.error}"])
        lines.append("")
    for names in products or []:
        lines.extend(_frequency_lines(round_, names))
        lines.append("")
    lines.append(f"saved: {directory}")
    return "\n".join(lines)


def _model(r) -> str:
    served = r.answer.served_model if r.answer else ""
    return f"{r.model} -> {served}" if served and served != r.model else r.model


def _place(r) -> str:
    if r.locale is None:
        return ""
    ignored = r.answer.locale_ignored if r.answer else []
    note = f", {' and '.join(ignored)} ignored by the API" if ignored else ""
    return f" [{r.locale}{note}]"


def _frequency_lines(round_: Round, names: list[str]) -> list[str]:
    lines = [f"{names[0]}: named in"]
    for f in frequency(round_, names):
        places = ", ".join("-" if p is None else f"#{p}" for p in f.positions)
        where = f"{str(f.locale):<9}" if round_.locales else ""
        lines.append(
            f"  {f.provider:<11} {where}{f.share} runs   positions: {places or '-'}   ({f.model})"
        )
    return lines


def _answer_lines(answer: Answer) -> list[str]:
    lines = [answer.text]
    if answer.sources:
        lines += ["", "sources:"]
        lines += [f"  - {s.title} <{s.url}>" if s.title else f"  - {s.url}" for s in answer.sources]
    return lines
