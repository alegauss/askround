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
