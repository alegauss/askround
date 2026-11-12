"""askround as an MCP server, so an agent can ask other assistants itself.

On 12/11/2026 the analysis stopped four times for a person to type a question into
ChatGPT and paste the answer back. `askround mcp` serves the same commands as tools over
stdio (newline-delimited JSON-RPC 2.0, the MCP stdio transport), with no dependency:

    askround_ask     ask one question across providers; the report, and the answers listed
    askround_answer  one answer's full text, from a round already asked
    askround_run     run a prompt set (a product file); the set's report
    askround_research  a research question everywhere, its claims merged by support
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
        "description": "Ask one question to several AI assistants (OpenAI, Gemini, Anthropic, Perplexity) with web search, each several times, and read what they recommend. Returns a brief of a few hundred tokens: for each product the runs naming it and its best position per provider, its top claims and the rivals, each fact with the ids of the answers it came from ('openai#2'). Read an answer, or the passage behind a fact, with askround_answer; detail: true returns the full report instead. Refused before any call if the question names a product it tests, carries personal data, or is estimated above max_cost.",
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
                "detail": {"type": "boolean", "description": "the full report, not the brief"},
            },
            "required": ["question"],
            "additionalProperties": False,
        },
    },
    {
        "name": "askround_answer",
        "description": "One answer from a round already asked, by the id a brief gives ('openai#2'): its full text and sources, or with `around` only the passage around that quote - the cheap way to check a fact.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "round": {
                    **_STR,
                    "description": "the round's directory, as the brief's 'round' gives it",
                },
                "answer": {
                    **_STR,
                    "description": "the answer's id, e.g. 'openai#2' or 'openai@BR#2'",
                },
                "around": {**_STR, "description": "a quote: return only the passage around it"},
                "provider": _STR,
                "run": {"type": "integer", "minimum": 1},
                "locale": {**_STR, "description": "when the round was asked in several locales"},
            },
            "required": ["round"],
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
        "name": "askround_research",
        "description": "Ask a research question to every assistant with web search and merge the answers: the claims they make, how many providers support each, each provider's passage, and the sources they cited with primary ones (repositories, licence texts, papers, official docs) first. Support is agreement among assistants, not proof.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": _STR,
                "providers": _PROVIDERS,
                "runs": {"type": "integer", "minimum": 1, "description": "default 1"},
                "max_cost": _COST,
            },
            "required": ["question"],
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
    if args.get("detail"):
        return {"round": data["saved"], "report": report_.build(round_, products, str(path))}
    return report_.brief(round_, products, data["saved"])


AROUND = 300  # characters either side of a quote in a passage


def _parse_id(answer_id: str) -> tuple[str, str | None, int]:
    """'openai#2' -> ('openai', None, 2); 'openai@BR#2' -> ('openai', 'BR', 2)."""
    head, _, run = answer_id.partition("#")
    provider, _, country = head.partition("@")
    if not provider or not run.isdigit():
        raise ToolError(f"{answer_id!r} is not an answer id such as 'openai#2' or 'openai@BR#2'")
    return provider, country.upper() or None, int(run)


def _target(args: dict) -> tuple[str, str | None, int]:
    if args.get("answer"):
        return _parse_id(args["answer"])
    if args.get("provider") and args.get("run"):
        country = (args.get("locale") or "").split(":")[0].upper() or None
        return args["provider"], country, args["run"]
    raise ToolError("give the answer's id ('openai#2'), or provider and run")


def _find(results: list[dict], provider: str, country: str | None, run_: int) -> dict | None:
    for r in results:
        locale = ((r.get("locale") or {}).get("country") or "").upper() or None
        same = r["provider"] == provider and r.get("run", 1) == run_
        if same and (country is None or locale == country):
            return r
    return None


def answer(args: dict, out: str | None) -> dict:
    """One answer by its id; with `around`, only the passage around that quote."""
    provider, country, run_ = _target(args)
    path = report_.find_round(Path(args["round"]), Path(out or "."))
    found = _find(json.loads(path.read_text(encoding="utf-8"))["results"], provider, country, run_)
    if found is None:
        raise ToolError(f"no answer {provider} run {run_} in {path}")
    locale = (found.get("locale") or {}).get("country")
    head = {
        "answer": f"{provider}{'@' + locale if locale else ''}#{run_}",
        "model": found.get("served_model") or found["model"],
        "error": found.get("error"),
    }
    text = found.get("text") or ""
    if args.get("around"):
        return {**head, "passage": _passage(text, args["around"])}
    return {**head, "text": text, "sources": found.get("sources") or []}


def _passage(text: str, quote: str) -> str:
    """The text around the quote, or a refusal naming that it is not there (law L4)."""
    at = text.find(quote)
    if at < 0:
        at = text.lower().find(quote.lower())
    if at < 0:
        raise ToolError("that quote is not in the answer's text")
    start, end = max(0, at - AROUND), min(len(text), at + len(quote) + AROUND)
    return ("..." if start else "") + text[start:end] + ("..." if end < len(text) else "")


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


def research_(args: dict, out: str | None, post=None) -> dict:
    argv = ["research", args["question"], "--json"]
    for name in args.get("providers") or []:
        argv += ["--provider", name]
    if args.get("runs"):
        argv += ["--runs", str(args["runs"])]
    if args.get("max_cost") is not None:
        argv += ["--max-cost", str(args["max_cost"])]
    return _json(argv + (["--out", out] if out else []), post)


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
        "askround_research": lambda: research_(args, out, post),
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
