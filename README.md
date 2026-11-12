# askround

People now ask ChatGPT or Gemini which app to use, and you cannot see the answer they
get. askround asks the assistants for you: the same question to OpenAI, Gemini,
Anthropic and Perplexity, with web search on, several times each. It tells you whether
your product is named and in which position, which rivals sit around it, what the
answers claim about it, and which of your pages they cite.

A real run, from 12/11/2026: four questions about Modelado, a Windows photo-to-3D app,
one run each on two providers (`askround run examples/modelado.toml --runs 1`):

| # | question | purpose | openai | gemini |
|---|---|---|---|---|
| 1 | What is a free offline app to turn a photo into a 3D model on Windows? | generic | 0/1 | 0/1 |
| 2 | What app can turn a photo into a 3D model on Windows without an NVIDIA GPU (AMD or CPU only)? | constraint | 1/1 | 0/1 |
| 3 | What Windows app can turn a photo into a relief STL for 3D printing? | use case | 0/1 | 0/1 |
| 4 | Qual app de Windows transforma uma foto em modelo 3D usando só a CPU, sem placa NVIDIA? | language | 1/1, #1 | 0/1 |

Each cell is the number of runs that named the app, then its position. ChatGPT finds
Modelado when the asker has no NVIDIA card, and Gemini doesn't find it at all. That is
who the app is for, and what its first screen has to say.

**askround measures the APIs, not the apps.** An API answer with web search is close to
what the chat apps say but not the same page: the apps add memory, personalisation and
their own choice of model. askround records what produced each answer (the model asked
for and the one that answered, the search tool, the settings, the time), and every
report is about the API.

```
pip install askround          # from a checkout until the first release: pip install .
askround doctor               # which providers have a key
askround ask "What app can turn a photo into a 3D model on Windows without an NVIDIA GPU?" \
    --product "Modelado,alegauss.github.io/modelado" --extract
```

Python 3.11 or later and the standard library only, so nothing in it is specific to one
system; it is tested on Windows.

Every provider whose API key is in the environment is asked in parallel:
`OPENAI_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), `ANTHROPIC_API_KEY` and
`PERPLEXITY_API_KEY`. askround reads the keys at call time and never stores them.
`askround doctor` lists which providers can run here: the key variable (never its
value), the model, the search tool and a free check call; `--no-check` makes no call.

Web search is on, through each provider's own search tool, because that is how
assistants find and recommend products. Each answer is printed with the sources it
cited. `--no-search` asks the same question without search, to compare.

Each round is saved under `.askround/rounds/<date>/<time>-<question>/` (change it with
`--out` or `ASKROUND_DIR`): `round.json` holds the question and each provider's answer,
search queries and sources, and `<provider>-<run>.json` the raw response as the provider
sent it. Assistants answer differently from one run to the next, so a product is
reported as "named in 2/3 runs, positions #1, #3, -", never from a single answer.

| Option              | What it does                                        |
| ------------------- | --------------------------------------------------- |
| `--provider NAME`   | ask only this provider (`openai`, `gemini`, `anthropic`, `perplexity`), repeatable |
| `--model PROVIDER=MODEL` | pin the model one provider uses, e.g. `openai=gpt-5-2025-08-07`, repeatable |
| `--no-search`       | ask without web search                              |
| `--runs N`          | ask each provider N times, in fresh conversations (default 3) |
| `--product NAME[,ALIAS...]` | report how many runs named the product and its position in each, repeatable |
| `--extract [PROVIDER]` | read each answer's recommendations in order with a model (one extra call per answer), so "Best fit" in a table or "my first choice" in prose ranks the product first |
| `--locale COUNTRY[:LANG]` | ask as someone in this country, e.g. `BR:pt-BR`; repeat to compare countries side by side |

Without `--extract`, a product's position is read from the answer's text: its place
among the top-level list items, numbered headings and table rows. With it, a small model
(gpt-5-mini, gemini-2.5-flash or claude-haiku-5-5, whichever has a key; override with
`ASKROUND_EXTRACT_MODEL`) lists what the answer recommends in its own order, each with a
quote. The text stays the check: a product counts as named only if its name is in the
answer, and a quote not found in the answer is marked `(?)`. Positions ranked this way
show a `*`.

Give the product's own places among its names, anything with a dot: a domain or a URL
prefix (`--product "Modelado,alegauss.github.io/modelado,github.com/alegauss/modelado"`).
The report then says, per provider, how many answers cited one of its pages and which
kind (site, repository, store, docs), and `round.json` lists every page and the
third-party domains cited. Tracking parameters are dropped; Gemini's redirect links are
counted by the domain in their title.

`--check-links` follows every link an answer writes beside the product's name (in its
table row or list item, or close to it in prose), images included, and flags those that
land on someone else's page, such as another app's Store page shown for yours, or that
are broken. A page counts as the product's when it is on one of its places or its
title names it.

With `--extract`, the report also lists what the answers claim about the product, from
tables and prose: `CPU only: Check build`, `Cost: Free, open-source`, each with the
providers that said it and the passage it came from. A claim whose quote is not in the
answer is counted apart and never shown as a finding.

With `--extract`, the report also lists the rivals: every other product the answers
recommend, with how many answers named it, its rank in each and which providers did
(the first ten in the report, all of them in `round.json`, each with the quote that
recommends it).

Each API takes a different part of a locale, and only for its search: OpenAI,
Anthropic and Perplexity an approximate country, Gemini a language. What a provider
cannot take is recorded on the answer and shown as "ignored by the API". Write the
question in the language you are testing: that is still the strongest signal.
| `--out DIR`         | where the round is saved                            |
| `--json`            | print the round as JSON                             |

A rate limit, a server error, a timeout or a dropped connection is retried up to three
times with backoff (honouring `Retry-After`); a rejected key or a missing model is not.
An answer that still fails is recorded with its error, the rest of the round carries
on, and the report lists the failures at the end.

The model per provider is overridden with `ASKROUND_OPENAI_MODEL`,
`ASKROUND_GEMINI_MODEL`, `ASKROUND_ANTHROPIC_MODEL` and `ASKROUND_PERPLEXITY_MODEL`.

## A product file, and the facts the answers get wrong

```toml
# modelado.toml
[product]
name = "Modelado"
places = ["alegauss.github.io/modelado", "github.com/alegauss/modelado"]

[[fact]]
attribute = "Runs without an NVIDIA GPU"
value = "Yes: any DirectX 12 GPU through DirectML, or the CPU"
page = "https://alegauss.github.io/modelado/"   # where it should be said plainly
```

`askround ask "..." --product-file modelado.toml --extract` asks about the product the
file describes and compares what the answers claim with its facts, in one more call: a
claim that contradicts a fact, or doubts it ('CPU only: Check build'), is reported as a
fact gap with the page that should state the fact plainly and the product's pages the
answers did cite.

## What a round costs

Before a round, askround prints an estimate from the number of calls, the tokens a
searched answer usually takes and each provider's prices, and refuses a round above the
cap you set (`--max-cost 0.50`, or `ASKROUND_MAX_COST`) before anything is sent. After
it, the report gives the actual cost per provider from the usage each API reported,
the extraction pass included.

The prices are a dated table in `askround/costs.py`: Anthropic's from its model table
of 2026-11-03, the others the last known list prices, to be checked against the
providers' pages. `ASKROUND_PRICES` names a JSON file that replaces any of them:
`{"models": {"gpt-5": {"input": 1.25, "output": 10.0}}, "search": {"openai": 0.01}}`.

### A budget an agent cannot raise

Set what askround may spend in its config file, `%APPDATA%\askround\config.toml` on
Windows, `~/.config/askround/config.toml` elsewhere (or the file `ASKROUND_CONFIG`
names):

```toml
[budget]
day = 1.00
month = 10.00
```

Every saved round adds its actual cost to `spent.jsonl` beside the rounds. A run whose
estimate would pass the day's or the month's budget is refused before any call
(`budget.over`): it waits for you. You approve it by running it with `--approve`, or
raise the budget; an agent using the MCP tools cannot do either, and every paid result
it gets says what has been spent against the budget. `askround budget` shows it.

### The same question twice costs once

A question asked again the same way within a day (the same text, providers, models,
locales and search, as many runs, extraction if wanted) returns the stored round, marked
with its age, and calls no provider. A round where some answers failed is asked again.
`--fresh` (or `fresh: true` over MCP) asks anew; the window is set in the config file:

```toml
[reuse]
max_age_hours = 24   # 0 turns reuse off
```

## Prompt sets: the same questions every week

Add `[[question]]` entries to the product file and it becomes a prompt set:

```toml
[[question]]
text = "What app can turn a photo into a 3D model on Windows without an NVIDIA GPU?"
purpose = "constraint"     # generic, constraint, use case, language
locale = "BR:pt-BR"        # optional
runs = 3                   # optional
```

A question that names the product it tests (its name, an alias, one of its places, or
a phrase listed under `phrases`) measures nothing, so it is refused before anything is
paid for. A question that asks about the product on purpose is marked `brand = true`
(or `--brand` on `ask`); it runs, and is reported apart.

A round sends the same text to every provider, so a question that carries personal data
(an email address, a phone number, a CPF, an IP address, an API key, or a name on your
own list in `ASKROUND_PRIVATE` or the file `ASKROUND_PRIVATE_FILE` names) stops before
anything is sent, naming the question and what it found.

`askround run modelado.toml` asks every question as its own round, kept together in
one set directory, and prints one table of question by provider before each question's
report. `askround report` on the set's directory prints it again.
[`examples/modelado.toml`](examples/modelado.toml) is the set this tool was built from.

## Which question leads to the product?

```
askround discover modelado.toml --seed "free offline app photo to 3D model on Windows"
```

From the seed and the product file's facts, a model writes variants (a constraint the
product meets, a use case, another language) that never name the product; askround
runs them with the seed and ranks them by how often and how high the product appears.
It runs once per question by default, which is a sketch: add the promising questions
to the product file and `askround run` them with more runs.

## Does a recommended product exist?

```
askround lookup "MeshForge3D" "Modly" --context "a Windows photo-to-3D app"
askround ask "..." --extract --check-rivals     # the top 10 rivals of a round
```

Each name is looked up on GitHub first (free; a repository of that name with at least
10 stars), then with one searched call on OpenAI, Anthropic or Gemini, which answers
found, ambiguous or not found with the page. A "found" whose page is not among the
pages that search returned is downgraded to ambiguous. `--no-web` keeps it to GitHub.
The report marks each checked rival, and names the ones found nowhere.

## The series

Every round saved also appends one line per answer to `series.jsonl` beside the rounds:
when, which question and set, which provider and model, and what was read (each
tracked product's mention and position, the recommendations, the cited pages, the
claims). It is an index of the rounds, so `--rebuild` writes it again from them.

```
askround series --product Modelado                     # answers naming it, per week
askround series --product Modelado --by day --question nvidia
```

`askround diff` compares the latest two runs of the same questions (or two you name)
and lists only what changed, per question and provider: the product's share and best
position, rivals that appeared or left, its pages newly cited or no longer cited, and
claims made or dropped.

## Export, and a weekly round

`askround export --product Modelado` writes the product's numbers from the series, one
row per day, provider and question (answers, named, frequency, best and mean position,
rivals, its pages cited), as CSV, JSON, or with `--format daily` in the shape a
`daily.json` of numbers per product takes (`{product: {day: {"assistants": {...}}}}`).
`--from`/`--to` bound the days and `--file` writes it out.

askround does not schedule itself; the system does. Every Monday at 08:00, on Windows:

```
schtasks /Create /SC WEEKLY /D MON /ST 08:00 /TN askround-modelado ^
  /TR "cmd /c cd /d D:\work && askround run modelado.toml --extract --max-cost 2 && askround export --product Modelado --format daily --file modelado-assistants.json"
```

and with cron:

```
0 8 * * 1  cd ~/work && askround run modelado.toml --extract --max-cost 2 && askround export --product Modelado --format daily --file modelado-assistants.json
```

The keys come from the environment the task runs in; `--max-cost` keeps an unattended
run from spending more than you agreed to.

## The report

```
askround report                     # the latest round, as Markdown
askround report <round dir> --json  # one round, as JSON for a pipeline
askround report --product Blender   # the same round, read for another product
```

`report` reads a stored round back and sums it up: for each product, a table of
provider by share of runs and positions, what the answers claim about it, which of its
pages they cite, then the rivals. The JSON holds the same facts and never the answers'
text, which stays in `round.json`.

## Research mode

```
askround research "Which open-source image-to-3D models allow commercial use?"
```

asks every provider once with search, reads each answer for the factual statements it
makes (each with a quote found in the answer), merges the statements that say the same
thing, and lists the claims by how many providers support them, each with every
provider's passage and the sources, those naming the claim's subject first and primary
ones (repositories, licence texts, papers, official docs) before secondary ones.
Support is agreement among assistants, not proof: check a claim at its primary source.

Where the assistants disagree on a fact (one says a model's licence allows commercial
use, another that it does not), the report opens with it: both sides, their passages,
and the primary sources to read to settle it.

## For agents: the plugin and the MCP server

In Claude Code, the plugin installs the MCP server and a skill that tells the agent to
run a question across assistants itself, instead of asking you to paste ChatGPT's
answer (askround itself must be installed, `pip install -e .`, and on the PATH):

```
/plugin install askround --marketplace alegauss/askround
```

or the server alone: `claude mcp add askround -- askround mcp`. Either serves:

| Tool | What it does |
| --- | --- |
| `askround_ask` | ask a question across providers; returns the report and lists the answers |
| `askround_answer` | the full text of one answer, with its sources |
| `askround_run` | run a prompt set (a product file); returns the set's report |
| `askround_research` | a research question everywhere, its claims merged by support |
| `askround_job` | a round started with `background: true`: its progress, then its result |
| `askround_report` | the report of a stored round or set |
| `askround_diff` | what changed between two runs of the same questions |
| `askround_doctor` | which providers can run (key variable names, never values) |

The same refusals hold for an agent: personal data, a question naming its product, and
a run estimated above `max_cost` (or `ASKROUND_MAX_COST`) stop before anything is
paid for.

`askround_ask` returns a brief: a few hundred tokens for a whole round (a real 2x2 round
with extraction: 614 characters, against 12,253 of answers). Each fact in it carries the
ids of the answers it came from (`openai#2`, `openai@BR#2`); `askround_answer` with an
id returns that answer, or with `around: "<quote>"` only the passage behind the fact.
`detail: true` returns the full report. On the command line: `askround report --brief`.
`askround_run` returns one brief per question in the set, and `detail: true` the set's
full report.

What each response costs the agent, measured on the recorded rounds in `tests/fixtures`
(two providers, three runs, extraction on; one token per four characters of JSON, so
an approximation, the same way for every tool):

| Response | Tokens | Budget |
| --- | ---: | ---: |
| `askround_ask` (brief) | 304 | 400 |
| `askround_ask` with `detail: true` | 1,360 | 1,800 |
| `askround_answer` | 868 | 1,100 |
| `askround_answer` with `around` | 175 | 250 |
| `askround_research` | 163 | 250 |
| `askround_run` (one question per purpose) | 760 | 1,000 |
| `askround_report` | 1,136 | 1,500 |
| `askround_diff` | 112 | 200 |
| `askround_doctor` | 257 | 350 |

The budgets live in `budgets/mcp-tokens.json` and `tests/test_tokens.py` fails a response
over its budget, so a field added to a response is a reviewed change. `pytest -s -k
figures` prints the table again.

A round takes minutes. With `background: true`, `askround_ask` and `askround_run` check
and estimate it, start it in a process of its own and return a job id at once; the
agent keeps working and reads it with `askround_job`: running (with how many answers
are in), done (with its brief), refused, failed, or interrupted. Each answer is written
the moment it lands, so an interrupted job keeps every answer it finished. The jobs
live in `jobs/` beside the rounds; `--estimate-only` on the command line runs the same
checks and prints the estimate without asking anything.

## Refused before it is paid for

Every check that needs no call runs before the first one, and a refusal lists every
problem at once, each with a code and the change that passes it:

```
askround: refused before anything was sent: 2 problem(s)
  [question.leading] the question names the product it tests (Modelado): 'Is Modelado good?'
      fix: Reword it as a person who does not know the product would ask; or ...
  [cost.over-cap] the estimate $0.2972 is above the cap $0.0010
      fix: Ask fewer providers or fewer runs, drop --extract, or raise the cap ...
```

`askround explain <code>` says what a code means; `askround explain` lists them. For an
agent, the MCP schemas carry the same limits (a question's length, the providers that
have a key), so a call that would be refused fails at the schema.

## The output contract

Every command takes `--json` (`export` takes `--format json`). Each JSON object names
its schema, `"schema": "askround/round@1"`, and the schemas are published in
[`schema/`](schema/) as JSON Schema. In a round, every fact says where it came from: the
answer's id (`openai#2`, `openai@BR#2`) and the character range of its passage in that
answer's text (`"range": [412, 437]`, end excluded), so a script or an agent can cite it.

| Exit code | Means |
| --- | --- |
| 0 | every answer came back |
| 3 | a partial round: it finished, some answers failed (they are listed) |
| 1 | no answer came back |
| 2 | refused before anything was sent (personal data, a leading question, over the cost cap, no key) or a usage error |

## Development

```
pip install -e .[dev]
python -m pytest                     # no key and no network: a test that calls out fails
python -m ruff check .
python -m ruff format --check .
ASKROUND_LIVE=1 python -m pytest -m live   # each adapter with a key, against its real API
```

The adapters are tested against real responses recorded from a live round
(`tests/fixtures/`, ids scrubbed), so a provider changing its shape shows up as a
failing recording rather than a silent miss.
