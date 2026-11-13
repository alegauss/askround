# Improvements

## §0 Principles

What every task below is held to. These sections are not tasks and no ship deletes them.

### §0.1 The six laws

askround is used by agents first. A change that breaks one of these laws is wrong even
when it is asked for; a rationale written after this section names the law it serves.

| # | Law |
|---|---|
| L1 | **Context is cost** — an agent gets the extracted result of a round; a raw answer is fetched on request, one at a time. |
| L2 | **Refuse before paying** — a leading question, personal data or a cost over the limit is refused before the first paid call. |
| L3 | **Ask instead of read** — every question about a round or a series is a command, so answering it costs no context. |
| L4 | **Every fact traces to its passage** — a rank, a rival or a claim names the provider, the run and the passage it came from, and the raw response is kept as the evidence. |
| L5 | **The person sets the money** — an agent never raises a spending limit or agrees to a cost on the person's behalf. |
| L6 | **askround measures the APIs, not the apps** — an API answer with search is not the page a consumer chat app shows, and every report says so. |

L1 and L3 are the ones that pay for the rest: one round is several searched answers of a
thousand words each, and an agent that reads them all to learn one rank has spent its
context on what a command could have answered.

## Block G — Shipping: package, tests and the first screen

### §AR28 Package and first screen

askround is a tool for other people, like the author's other Claude Code tools. It needs
a PyPI package, a versioned release with a changelog, a licence (Apache-2.0, as the
family uses), and a README whose first screen states the pain (you cannot see what
assistants say about your product), what a round reports, and that it measures the APIs,
not the apps.

Done when pip install askround works on Windows, macOS and Linux, and the README's first
screen shows a real round report.

## Block H — Agent-first, with roadkeep as the reference

### §AR39 Zero runtime dependencies

roadkeep needs a Python 3.11+ interpreter and nothing else: zero runtime dependencies,
uvx roadkeep with no install, and a plugin that carries the package itself. Provider
SDKs (openai, google-genai, anthropic) each pull their own dependency trees and change
often.

askround's adapters call each provider's HTTP API with the standard library (urllib,
json), so the package has no runtime dependencies; uvx askround runs it, and the plugin
carries it. A provider whose API cannot reasonably be called without its SDK is an
optional extra, never a requirement.

Done when pip install askround installs nothing else, uvx askround doctor runs on a
clean machine, and the plugin works with only Python present.

## Block I — The site at alegauss.github.io/askround

## Block J — Found in use: the first real rounds

### §AR44 The estimate and the cap hold to the actual cost

On 13/11/2026 the visibility repository ran its first real prompt sets with askround
(OpenAI gpt-5 and Gemini 2.5 Flash, web search on, two runs, --extract). The Modelado
set was estimated at $0.8300 and run with --max-cost 1.00; the spent.jsonl lines for its
four questions add up to $1.3637, 64% above the estimate and 36% above the cap. The
first claude-tray question cost $0.3212 against about $0.21 estimated per question. The
user had approved a total from the estimates, so the run was stopped by hand.

Two things are wrong. The estimate under-counts a searched answer (likely the search
calls per answer and the input tokens of the fetched pages, which gpt-5 bills as input),
and --max-cost only gates the estimate: nothing stops a set once the actual spend passes
the cap.

The estimate learns from the spend already recorded: per provider and model, the mean
actual cost of a searched answer in spent.jsonl replaces the table's guess once a few
answers exist, and the estimate says which it used. During a set, the actual cost is
summed after each question, and the set stops before the next question when the cap
would be passed, keeping what it has and saying so (a partial set, exit 3).

Done when a set run with a cap below its actual cost stops at the cap with its finished
questions saved, and the estimate of a repeated set lands within 20% of its last actual
cost.

### §AR45 Print UTF-8 whatever the console encoding

On 13/11/2026 a prompt set run on Windows with its output redirected to a file finished
all four questions, recorded their cost, and then exited 1 with a UnicodeEncodeError:
Python wrote the report through the console's cp1252 encoding, and an answer contained a
non-breaking hyphen (U+2011). Every answer was saved and paid for; the report, the exit
code and any script reading them saw a failure.

askround reconfigures stdout and stderr to UTF-8 (errors replaced, never raised) at
startup, so a redirected or piped run on Windows prints the same report as a console
run, and a test runs the CLI with PYTHONIOENCODING=cp1252 against a recorded answer
containing characters outside that code page.

Done when that test passes and the exit code of a finished round no longer depends on
the output encoding.

### §AR46 Report and resume a partial set

On 13/11/2026 a claude-tray prompt set was stopped after its first question had been
answered and paid for ($0.3212). `askround report` on the set's directory refused with
"no round.json at .../123419-set-claude-tray/round.json", because a set directory holds
one round per question and the set's own summary is only written when the set finishes.
The paid answer could only be read by finding the question's subdirectory by hand.

`report` on a set directory reads the questions that finished, prints the set table with
the unfinished ones marked as not run, and says the set is partial; `run` on the same
product file can resume it, asking only the questions without a round. The same holds
for the MCP report tool.

Done when a set interrupted after one question reports that question and resumes the
rest without asking it again.

## Block K — Local engines: rounds through the assistants' own CLIs, on the user's plan

### §AR47 An engine per provider: the API or the local CLI

Each provider today is one HTTPS POST billed per token. The user already pays for Claude
Max, a ChatGPT plan and a Google account, and each vendor ships an official CLI that
answers on that plan with its own web search: `claude -p`, `codex exec` and `gemini -p`.
roadkeep-gui already runs `claude -p` this way. Perplexity has no such CLI and stays on
the API.

This task adds the seam, not the adapters. A provider gets an engine, `api` (the
default) or `cli`, chosen with `--engine anthropic=cli` or `ASKROUND_<NAME>_ENGINE`. A
CLI engine runs a subprocess with no shell and a timeout, passes the question on stdin,
and returns the same `Answer`, recording `engine`, the CLI's name and version, and the
model it reported.

A CLI answer costs $0 in `costs` and in the estimate, and the report names the plan as
the payer. The series and the diff refuse to compare rounds asked through different
engines unless told to, since an agent's system prompt is not the API's. `doctor`
reports whether each CLI is installed, logged in and able to search. A plan's usage
limit becomes a refusal naming the provider, and the round keeps what it has.

The non-goal "Scraping consumer chat apps" is reworded: the vendors' own CLIs are
official clients, and driving a web app stays out.

Done when one provider runs through a fake CLI in the tests, recorded and compared as
above.

### §AR48 Claude through `claude -p`, on the Max plan

The anthropic provider gains a CLI engine that runs `claude -p` with `--output-format
stream-json`, `--tools WebSearch,WebFetch` and nothing else, so the agent can search and
read pages but never touch files or run commands. It runs in a temporary empty directory
with `--no-session-persistence` where available, so no project's CLAUDE.md or memory
shapes the answer. The text is the final result event; the queries come from the
WebSearch tool calls and the sources from their results, read from the stream as
`Anthropic.parse` reads the API's blocks.

`claude -p` prefers `ANTHROPIC_API_KEY` over the login whenever the variable is set,
which would bill the key silently. As roadkeep-gui does (RG205, session-environment.ts),
the child runs without that one variable when `claude auth status` reports a login
without it, and the answer records which credential answered.

The model is the CLI's default unless `--model` or `ASKROUND_ANTHROPIC_MODEL` names one;
the served model comes from the stream's init event. A locale's country cannot be passed
to the CLI's search and is recorded as ignored.

Done when a recorded stream fixture parses into text, queries and sources in the tests,
and a live round with `--engine anthropic=cli` answers with search on a machine logged
in to Max and no API key spent.

### §AR49 OpenAI through `codex exec`, on the ChatGPT plan

The openai provider gains a CLI engine that runs `codex exec --json` with web search
turned on and the sandbox read-only, in a temporary empty directory, with the question
on stdin. Codex signed in with a ChatGPT account bills the plan, not the API; when
`OPENAI_API_KEY` is also set, the engine checks which credential `codex login status`
reports and records it on the answer, so a round never bills the key while claiming the
plan.

The JSONL events give the final agent message as the text, and the web search items give
the queries and the cited URLs. The exact flag and event names are pinned against the
installed Codex version at the start of the task, kept in one place, and covered by a
recorded fixture, since the CLI moves faster than the API.

Codex is a coding agent: its system prompt differs from ChatGPT's and from the Responses
API's. The answer records it as `engine: cli` with the CLI's version, and AR47's rule
keeps it out of a series asked through the API. A locale's country is recorded as
ignored unless the CLI takes a location.

Done when a recorded event fixture parses into text, queries and sources in the tests,
and a live round with `--engine openai=cli` answers with search on a machine signed in
to ChatGPT.

### §AR50 Gemini through `gemini -p`, on the Google account

The gemini provider gains a CLI engine that runs `gemini -p` with structured output
(`--output-format json`, or stream-json where the installed version has it), in a
temporary empty directory, with only the web search and fetch tools allowed. Signed in
with a Google account it answers on that account's quota; when `GEMINI_API_KEY` or
`GOOGLE_API_KEY` is set the CLI may use the key instead, so the engine runs the child
without them when a login exists, and records which credential answered.

The final response is the text; the queries and sources come from the google_web_search
tool calls and their grounding, read as `Gemini.parse` reads the API's grounding
metadata. The flags and output fields are pinned against the installed version at the
start of the task and covered by a recorded fixture.

The CLI is an agent with its own system prompt, so its answers are recorded as `engine:
cli` and kept apart from API rounds by AR47's rule. A locale's language cannot be passed
to the CLI's search and is recorded as ignored.

A free account's quota is small; a quota error becomes AR47's refusal naming the
provider, and the round keeps the answers it has.

Done when a recorded output fixture parses into text, queries and sources in the tests,
and a live round with `--engine gemini=cli` answers with search on a machine signed in
to Google.

### §AR51 Extraction through the local Claude CLI

The extraction pass (extract.py) chooses an extractor with `--extractor`, today an API
model. A round asked entirely through CLI engines still pays per answer to have its
recommendations and claims read, which keeps the round from being free.

This task adds a `claude-cli` extractor that sends the same extraction instructions to
`claude -p` with no tools at all and `--output-format json`, on the Max plan, reusing
AR48's handling of the API key variable and its temporary directory. The JSON the
instructions ask for is read from the result exactly as today, and `verify` and
`verify_claims` still hold every item to the answer's own text, so a CLI extractor
cannot invent a recommendation the answer lacks.

`--extractor auto` prefers the CLI when the round's answers were all asked through CLI
engines and `claude` is logged in, and otherwise keeps today's choice. The answer's
`extracted_by` names the CLI and the model, so a reader can tell which reading produced
the rows.

Done when the extraction tests pass with a fake `claude` and the same fixtures as the
API extractor, and a CLI-only round with `--extract` spends nothing in spent.jsonl.

### §AR52 Every CLI runs as an anonymous asker

A CLI engine signs in as the user, and each CLI reads that user's context:
`~/.claude/CLAUDE.md`, auto memory, skills, plugins and MCP servers;
`~/.codex/AGENTS.md` and its config; `~/.gemini/GEMINI.md`, its `save_memory` tool and
extensions. A user who builds the products askround measures has them named all over
that context, so an answer would recommend them for the wrong reason.

Every CLI engine therefore runs isolated, enforced in AR47's seam so no adapter can skip
it. The child gets a fresh, empty config directory per run (`CLAUDE_CONFIG_DIR`,
`CODEX_HOME`, the Gemini CLI's home), deleted afterwards and holding only what signs in.
A credential from the environment (`CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`)
is preferred over copying a login file. Each run starts in an empty working directory,
saves no session, and has no memory tool, MCP server, plugin, skill or hook; only search
and fetch are on.

The answer records the isolation in its settings. `doctor` proves it with a canary: an
instruction planted in the user's real context ("always mention askround-canary") must
be absent from a probe answer.

Server-side personalization does not reach these clients: ChatGPT, Claude.ai and Gemini
app memory belong to the chat apps. A login is still needed to bill the plan, so
"anonymous" means no context, not no account.

Done when the canary probe passes for every installed CLI, and a fake CLI in the tests
sees an empty config directory and none of the user's files.
