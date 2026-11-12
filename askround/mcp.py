"""askround as an MCP server, so an agent can ask other assistants itself.

On 12/11/2026 the analysis stopped four times for a person to type a question into
ChatGPT and paste the answer back. `askround mcp` serves the same commands as tools over
stdio (newline-delimited JSON-RPC 2.0, the MCP stdio transport), with no dependency:

    askround_ask     ask one question across providers; the report, and the answers listed
    askround_answer  one answer's full text, from a round already asked
    askround_run     run a prompt set (a product file); the set's report
    askround_report  the report of a stored round or set
    askround_diff    what changed between two runs of the same questions
    askround_doctor  which providers can run (key variable names, never values)

Each tool runs the command line in-process, so every refusal holds for an agent too:
personal data, a question naming its product, a missing key, and the cost estimate
against the cap (law L2, L5) - before anything is paid for. Context is cost (law L1):
askround_ask returns what was read from the answers and lists them, and the text of
one answer comes from askround_answer, when the agent asks for it.

Register it with Claude Code: `claude mcp add askround -- askround mcp`.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from askround import __version__
from askround import report as report_

PROTOCOL = "2025-06-18"

_STR = {"type": "string"}
_PROVIDERS = {
    "type": "array",
    "items": {"type": "string", "enum": ["openai", "gemini", "anthropic", "perplexity"]},
    "description": "only these providers (default: every one with a key)",
}
_COST = {
    "type": "number",
    "description": "refuse, before any call, a run estimated above this (USD)",
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "askround_ask",
        "description": "Ask one question to several AI assistants (OpenAI, Gemini, Anthropic, Perplexity) with web search, each several times, and read what they recommend. Returns the report (for each product: share of runs naming it, positions, claims, cited pages; the rivals) and the answers listed by provider and run; read an answer's text with askround_answer. Refused before any call if the question names a product it tests, carries personal data, or is estimated above max_cost.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {**_STR, "description": "the question, as a person would ask it"},
                "products": {
                    "type": "array",
                    "items": _STR,
                    "description": "products to report on, each 'Name,alias,domain'",
                },
                "providers": _PROVIDERS,
                "runs": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "runs per provider (default 3)",
                },
                "extract": {
                    "type": "boolean",
                    "description": "read recommendations and claims with a model (one call per answer)",
                },
                "locales": {"type": "array", "items": _STR, "description": "e.g. ['BR:pt-BR']"},
                "search": {"type": "boolean", "description": "web search (default true)"},
                "max_cost": _COST,
            },
            "required": ["question"],
            "additionalProperties": False,
        },
    },
    {
        "name": "askround_answer",
        "description": "The full text of one answer from a round already asked, with the sources it cited.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "round": {
                    **_STR,
                    "description": "the round's directory, as askround_ask returned it",
                },
                "provider": _STR,
                "run": {"type": "integer", "minimum": 1},
                "locale": {**_STR, "description": "when the round was asked in several locales"},
            },
            "required": ["round", "provider", "run"],
            "additionalProperties": False,
        },
    },
    {
        "name": "askround_run",
        "description": "Ask every question of a product file (a prompt set) and return the set's report: one table of question by provider, then each question's report.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {**_STR, "description": "the product file (TOML)"},
                "providers": _PROVIDERS,
                "runs": {"type": "integer", "minimum": 1},
                "extract": {"type": "boolean"},
                "max_cost": _COST,
            },
            "required": ["file"],
            "additionalProperties": False,
        },
    },
    {
        "name": "askround_report",
        "description": "The report of a stored round or prompt set (default: the latest).",
        "inputSchema": {
            "type": "object",
            "properties": {"round": {**_STR, "description": "a round's or set's directory"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "askround_diff",
        "description": "What changed between two runs of the same questions (default: the latest two): share and rank, rivals, cited pages, claims.",
        "inputSchema": {
            "type": "object",
            "properties": {"old": _STR, "new": _STR, "product": _STR},
            "additionalProperties": False,
        },
    },
    {
        "name": "askround_doctor",
        "description": "Which providers can run here: the key variable each reads (never its value), the model and the search tool. Makes a free check call to each.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


class ToolError(Exception):
    """A refusal or failure, returned to the agent as an error result."""


def _cli(argv: list[str], post=None) -> tuple[int, str, str]:
    from askround.cli import main

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv, post=post)
        except SystemExit as exit_:  # argparse refusing an argument
            code = exit_.code if isinstance(exit_.code, int) else 2
    return code, out.getvalue(), err.getvalue()


def _json(argv: list[str], post=None) -> Any:
    code, out, err = _cli(argv, post)
    if code != 0:
        raise ToolError(_reason(err) or out.strip() or f"askround exited {code}")
    return json.loads(out)


def _reason(err: str) -> str:
    lines = [line.removeprefix("askround: ") for line in err.splitlines() if line.strip()]
    refusals = [line for line in lines if not line.startswith("estimated cost")]
    return "\n".join(refusals or lines)


def _common(args: dict, argv: list[str]) -> list[str]:
    for name in args.get("providers") or []:
        argv += ["--provider", name]
    if args.get("runs"):
        argv += ["--runs", str(args["runs"])]
    if args.get("extract"):
        argv.append("--extract")
    if args.get("max_cost") is not None:
        argv += ["--max-cost", str(args["max_cost"])]
    return argv


def ask(args: dict, out: str | None, post=None) -> dict:
    argv = _common(args, ["ask", args["question"], "--json"])
    for product in args.get("products") or []:
        argv += ["--product", product]
    for locale in args.get("locales") or []:
        argv += ["--locale", locale]
    if args.get("search") is False:
        argv.append("--no-search")
    if out:
        argv += ["--out", out]
    data = _json(argv, post)
    path = Path(data["saved"]) / "round.json"
    round_, products = report_.load_round(path)
    listed = [
        {
            "provider": r["provider"],
            "run": r["run"],
            "locale": (r.get("locale") or {}).get("country"),
            "model": r.get("served_model") or r["model"],
            "chars": len(r.get("text") or ""),
            "error": r.get("error"),
        }
        for r in data["results"]
    ]
    return {
        "round": data["saved"],
        "report": report_.build(round_, products, str(path)),
        "answers": listed,
        "cost": data.get("cost"),
    }


def answer(args: dict, out: str | None) -> dict:
    path = report_.find_round(Path(args["round"]), Path(out or "."))
    data = json.loads(path.read_text(encoding="utf-8"))
    for r in data["results"]:
        locale = (r.get("locale") or {}).get("country")
        if r["provider"] != args["provider"] or r.get("run", 1) != args["run"]:
            continue
        if args.get("locale") and (locale or "").upper() != args["locale"].split(":")[0].upper():
            continue
        return {
            "provider": r["provider"],
            "run": r.get("run", 1),
            "model": r.get("served_model") or r["model"],
            "text": r.get("text"),
            "sources": r.get("sources") or [],
            "error": r.get("error"),
        }
    raise ToolError(f"no answer from {args['provider']} run {args['run']} in {path}")


def run(args: dict, out: str | None, post=None) -> dict:
    argv = _common(args, ["run", args["file"]])
    if out:
        argv += ["--out", out]
    code, text, err = _cli(argv, post)
    if code != 0:
        raise ToolError(_reason(err) or f"askround exited {code}")
    saved = [
        line.removeprefix("saved: ") for line in text.splitlines() if line.startswith("saved: ")
    ]
    return report_.build_set(Path(saved[-1]) / "set.json")


def report(args: dict, out: str | None) -> dict:
    argv = ["report", "--json"] + ([args["round"]] if args.get("round") else [])
    return _json(argv + (["--out", out] if out else []))


def diff(args: dict, out: str | None) -> dict:
    argv = ["diff", "--json"] + [args[k] for k in ("old", "new") if args.get(k)]
    if args.get("product"):
        argv += ["--product", args["product"]]
    return _json(argv + (["--out", out] if out else []))


def doctor(args: dict, out: str | None, post=None) -> Any:
    return _json(["doctor", "--json"], post)


def call(name: str, args: dict, out: str | None = None, post=None) -> dict:
    """Run one tool; an MCP tool result, an error result when it is refused."""
    handlers = {
        "askround_ask": lambda: ask(args, out, post),
        "askround_answer": lambda: answer(args, out),
        "askround_run": lambda: run(args, out, post),
        "askround_report": lambda: report(args, out),
        "askround_diff": lambda: diff(args, out),
        "askround_doctor": lambda: doctor(args, out, post),
    }
    if name not in handlers:
        return _text(f"no tool named {name}", error=True)
    try:
        return _text(json.dumps(handlers[name](), ensure_ascii=False, indent=2))
    except (ToolError, FileNotFoundError, KeyError, ValueError) as error:
        return _text(str(error), error=True)


def _text(text: str, error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": error}


def handle(message: dict, out: str | None = None, post=None) -> dict | None:
    """One JSON-RPC message in, the response out (None for a notification)."""
    method, ident = message.get("method"), message.get("id")
    if ident is None:
        return None  # notifications/initialized and the like need no answer
    if method == "initialize":
        asked = (message.get("params") or {}).get("protocolVersion") or PROTOCOL
        result: Any = {
            "protocolVersion": asked,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "askround", "version": __version__},
            "instructions": "Ask other AI assistants a question and read what they recommend. Start with askround_doctor to see which providers can run; askround_ask returns a report, and askround_answer one answer's text.",
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        result = call(params.get("name", ""), params.get("arguments") or {}, out, post)
    else:
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "error": {"code": -32601, "message": f"no method {method}"},
        }
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def serve(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout, out: str | None = None) -> None:
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            reply: dict | None = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "not JSON"},
            }
        else:
            reply = handle(message, out)
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()
