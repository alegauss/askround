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

## Block C — Trust: checking what the answers say

### §AR13 Rivals that may not exist

On 12/11/2026 one answer listed two CPU-only alternatives that a later web search could
not find as Windows apps. A competitor table built from answers inherits whatever the
model invents.

Each rival extracted from a round is looked up (web search, GitHub, package registries,
app stores) and marked found, ambiguous or not found, with the evidence link. The report
flags the ones not found.

Done when the two names from 12/11/2026 come out flagged and Modly comes out found with
its repository.

### §AR14 Links that point elsewhere

On 12/11/2026 two answers illustrated Modelado with Microsoft Store pages of other apps
('Image to 3d model', 'AI Text & Image to 3D Generator Pro'), while its own Store page
existed but was a day old.

Every link and image source attributed to the product is resolved: status code, final
URL after redirects, and whether the page's title and domain belong to the product.
Mismatches are reported with the answer they came from.

Done when those two mismatches are flagged from the recorded answers and the product's
real pages pass.

### §AR15 Fact gaps

Modelado runs on the CPU and the README said so on line 96; the assistant still answered
'Check build', because no first screen said it. That gap became a task in the product's
roadmap only because a person compared the answer with the facts.

A product file lists its facts (runs without an NVIDIA GPU, price, licence, platforms),
each with the page that states it. askround compares the extracted claims with those
facts and reports each mismatch or doubt, with the pages the assistant cited and the
page that should carry the fact more plainly.

Done when the recorded answers produce the 'CPU only' gap pointing at the README and
site first screens.

## Block D — Questions: prompt sets and finding the question that leads to a product

### §AR16 Prompt sets

The questions of 12/11/2026 (the generic one, without NVIDIA, the relief for printing,
and the Portuguese CPU-only one) exist only in a chat transcript.

A prompt set is a file per product: its names and domains, and its questions, each with
a purpose (generic, constraint, use case, language), a locale and the number of runs.
`askround run <set>` runs the whole set as one round.

Done when the four questions of 12/11/2026 live in a prompt set and run as one round.

### §AR17 Discovering the question that leads to a product

The analysis guessed variants by hand: generic, without an NVIDIA GPU, relief for 3D
printing, Portuguese and CPU only. Only some named the product, and that set told which
feature brings people.

From the product's facts and a seed question, askround generates variants along each
axis (a constraint the product meets, a use case it serves, a language) without naming
the product, runs them, and ranks the variants by how often and how high the product
appears.

Done when, from the seed 'free offline app photo to 3D model on Windows' and Modelado's
facts, a discovery run ranks a no-NVIDIA variant above the generic one.

### §AR18 Leading questions

The tests on 12/11/2026 were written to stay neutral: no product name, no domain, no
wording copied from the product's page. That care was manual.

Before a round, every question is checked against the product's names, aliases, domains
and distinctive phrases, and a question that contains one is refused unless marked as an
intentional brand question, which the report keeps apart.

Done when a question containing the product's name or domain is refused and a marked
brand question runs and is reported separately.

### §AR19 No personal data in questions

The session that started askround worked under a rule that no personal details go to
outside services. A round multiplies any slip by the number of providers.

Before sending, each question is scanned for email addresses, phone numbers, personal
names from a configured list and other identifiers, and the round stops and names the
match. Product names and public domains are allowed.

Done when a question with an email address stops the round before any call and says
which question and why.

## Block E — Over time: the series, the diff, the cost and the export

### §AR20 The series

Each test on 12/11/2026 was a snapshot. Whether Modelado stays first after its page
changes, or whether a rival overtakes it, is a question about time.

Rounds are stored append-only (SQLite or JSON Lines), keyed by date, prompt set,
question, provider, model and run, with the extracted mentions, ranks, rivals, citations
and claims, so any later report can be computed from them.

Done when several rounds of the same set are stored and a query returns a product's
frequency per week per provider.

### §AR21 The diff

A weekly review wants to know what changed: a rival that appeared (as Modly did), a rank
lost on one provider, a page that stopped being cited, a claim that became correct after
the product's page changed.

`askround diff` compares two rounds of the same set and lists those changes, per
question and provider, in Markdown and JSON.

Done when two stored rounds that differ in rank, rivals and citations produce a diff
naming each change.

### §AR22 Cost estimate and budget

Proposing a weekly round on 12/11/2026, the agent could only say 'cents to a few dollars
a week, to confirm against current prices'.

Before a round, askround estimates its cost from the number of calls, the expected
tokens and each provider's search price, kept in a price table with its date; a budget
cap stops a round that would exceed it. After a round, it records the actual tokens and
searches each provider reports and the cost computed from them.

Done when a round prints its estimate, refuses one above the cap, and reports the actual
cost per provider.

### §AR23 Export and scheduling

The project that motivated askround collects numbers per product every day and builds a
dashboard from them. A weekly askround round should add rows there: date, product,
provider, question, frequency, best rank, rivals count, cited pages.

`askround export` writes those rows as CSV or JSON for a date range. Scheduling stays
outside askround (Windows Task Scheduler, cron, CI); the README shows how.

Done when an export of two rounds produces rows another project can load, and the README
documents a weekly schedule.

## Block F — For agents: an MCP server, a skill and research across assistants

### §AR24 An MCP server

The agent analysing Modelado knew which question to ask next but had no tool to ask it,
so each step waited for the user to type it into ChatGPT and paste the answer.

askround runs as an MCP server (stdio) with tools to ask a question across providers,
run a prompt set, and read a report or a diff, returning structured results the agent
can reason over. Cost estimates and the budget cap apply to agent calls too, and the
server never exposes keys.

Done when Claude Code, with the server configured, can ask a question across two
providers and read the answers without the user.

### §AR25 Research mode

Beyond visibility, the session needed research: which open image-to-3D models allow
commercial use, which competitors exist, what users ask for. Each was done by separate
searches and reading, with care to mark what was verified against what was inferred.

A research mode sends one research question to every provider with search, then merges
the answers: the claims, how many providers support each, the sources each cites, and
the primary sources (official repositories, licence texts) set apart from secondary
ones.

Done when a research question returns a merged answer with claims grouped by support and
sources ranked primary first.

### §AR26 Disagreements to check

During the model research, one third-party page described every Depth Anything 3
checkpoint as non-commercial, while the official table lists the Mono and Metric Large
ones under Apache-2.0. A merged answer that hides such a split invites a wrong decision.

Research mode marks every claim on which providers disagree, or on which one provider's
sources conflict, and lists the primary source to read to settle it.

Done when a research question with a known disagreement reports it with both sides and
the primary source to check.

### §AR27 A Claude Code skill

The author ships his Claude Code tools (roadkeep, commitclerk) with skills and plugins.
An agent that needs to know what assistants say about a product, or to research across
assistants, should reach for askround without being told.

A skill describes when to use askround (visibility of a product, finding the question
that leads to it, research across assistants), how to keep questions neutral and free of
personal data, and how to read a report; a plugin installs the MCP server and the skill
together.

Done when, in a fresh Claude Code session with the plugin, asking 'do assistants
recommend my app?' leads the agent to run a round.

## Block G — Shipping: package, tests and the first screen

### §AR28 Package and first screen

askround is a tool for other people, like the author's other Claude Code tools. It needs
a PyPI package, a versioned release with a changelog, a licence (Apache-2.0, as the
family uses), and a README whose first screen states the pain (you cannot see what
assistants say about your product), what a round reports, and that it measures the APIs,
not the apps.

Done when pip install askround works on Windows, macOS and Linux, and the README's first
screen shows a real round report.

### §AR29 Recorded fixtures

Every provider returns a different shape, with search metadata that changes between API
versions.

Each adapter is tested against recorded responses (with keys and identifying headers
stripped), including real answers as fixtures for the extraction tests (the 12/11/2026
answers were never kept verbatim, only summarised in visibility/estrategia/modelado.md,
so `tests/test_extract.py` uses synthetic answers in their shape; the first recorded
'without NVIDIA' round should replace them); a separate, opt-in live test checks each
adapter against its real API with the smallest call. CI runs only the recorded tests.

Today `tests/conftest.py` holds hand-written responses shaped from each provider's
documentation, not recordings. OpenAI and Gemini were run live when AR2 shipped; the
Anthropic and Perplexity adapters (web search tool, `pause_turn` resume, Sonar's
`search_results`) have never answered a live call, because no key was present, so their
first live run is the one most likely to find a wrong field.

Done when the test suite runs with no key and no network, and the live tests run when
keys are present and are asked for.

## Block H — Agent-first, with roadkeep as the reference

### §AR31 Ask instead of read

One answer from an assistant with search runs to a few thousand tokens, with tables,
links and follow-up questions. A round of four questions, four providers and three runs
is 48 of them. Handing those to an agent repeats what roadkeep was built against: a
roadmap whose words the agent reads again every turn. roadkeep answers with pick, brief
and list instead of letting the agent read the file.

By default every command and MCP tool returns the extracted result only (frequency,
ranks, rivals, cited pages, claims, failures), each item pointing to the answer it came
from by id. A separate call returns one raw answer, or the quoted passage behind one
claim, when the agent asks.

Done when a full round returns to the agent in a few hundred tokens, and any fact in it
reaches its passage with one more call.

### §AR32 --json everywhere, with provenance

Every roadkeep command takes --json, which also says which file and line the answer came
from, and its exit code is the whole contract a hook, a pre-commit hook and a GitHub
Action share. An agent parsing prose breaks when the wording changes and cannot cite
what it read.

Every askround command takes --json with a versioned schema published in the repository.
Each fact carries its provenance: round, question, provider, model, run, answer id and,
for a claim or a mention, the character range of its passage. Exit codes say success,
partial round, refused and failed, and are documented as the contract.

Done when every command has a JSON form validated against the published schema in tests,
and each fact in it resolves to its passage.

### §AR33 Refused before it is paid for

roadkeep puts its limits in its MCP input schemas, so a field that would be refused
fails before anything is written; every finding names the command that closes it, and
roadkeep explain says what a code means. A round has the same kind of mistake, except
each one costs money: a question that names the product, an email in a prompt, a
provider without a key, a cost above the budget.

Every check that can run before a call runs first: limits declared as maxLength and
enums in the MCP schemas (questions, providers that have keys, prompt sets that exist),
leading questions, personal data, missing keys, the estimate against the budget. A
refusal lists every problem at once, each with a code and the change that passes it, and
askround explain <code> describes the code.

Done when each of those cases is refused with no provider called, every refusal names
its fix, and explain covers every code.

### §AR34 Money needs the person's consent

The session that started askround could only estimate the cost of a weekly round. An
agent with an MCP tool can run rounds on its own, and every round with web search costs
money on the user's keys. roadkeep never spends anything; askround does, so it needs a
rule roadkeep did not.

The user sets a budget per day and per month in askround's config, which the agent
cannot change through the MCP tools. Within it, rounds run; a round that would pass it
is not run, and the tool returns the estimate and asks the person to approve it or raise
the budget. Spending so far is reported with every result.

Done when an agent's round above the budget returns an approval request with no provider
called, and the month's spending appears in every result.

### §AR35 Rounds as jobs

Dozens of calls with web search, each taking seconds to tens of seconds, make a round of
several minutes. roadkeep's tools answer in milliseconds; askround's cannot, and an MCP
tool that blocks that long freezes the agent and risks a client timeout that throws away
results already paid for.

A round can start as a job: the tool returns a job id and the estimate at once, progress
can be read, and the result is fetched when done, with finished answers kept if the job
is interrupted. A single question stays synchronous.

Done when an agent starts a round, keeps working, and reads the finished result later
through the MCP server, and an interrupted job keeps what it finished.

### §AR36 Reuse a recent round

An agent that lost a result from its context, or a second session on the same task, asks
the same question again, and each repeat pays for every search again.

A question already asked with the same provider, model and locale within a freshness
window (default one day, configurable) returns the stored result, marked with its age,
at no cost; a fresh run is an explicit flag, and it counts against the budget like any
other.

Done when a repeated question within the window returns the stored result with its date
and calls no provider.

### §AR37 A token budget in the tests

roadkeep started from measurements (142 words a line, a 186 KB agents.md, about 46k
tokens read every turn) and keeps its answers small on purpose. Responses grow one field
at a time, and nobody notices until the agent's context is full.

The tests run the recorded rounds through every MCP tool and count the tokens of each
response, against a budget per tool written in the repository. A response over its
budget fails the test, raising a budget is a reviewed change, and the README publishes
the figures as roadkeep does.

Done when every MCP tool has a token budget enforced by the recorded tests and the
README states it.

### §AR38 Wired like roadkeep

roadkeep installs with two commands at project scope, which write the marketplace and
the plugin into the repository's .claude/settings.json, so every clone is wired with no
step per machine. What arrives is the MCP server, slash commands, a skill loaded only
when relevant, and a hook; install writes the same into a project from a checkout,
install --check tells CI whether they are still in step, and a committed launcher covers
Claude Code on the web, which never installs a marketplace plugin.

askround ships the same way: a marketplace with the plugin at project scope, its MCP
tools, slash commands (ask, run, report, diff), the skill, install and install --check
from a checkout, and the launcher for the web. Its MCP schemas carry the project's own
prompt sets, providers and budget, as roadkeep's carry its limits.

Done when a repository that commits the settings gets askround's tools, commands and
skill on a fresh clone, and on Claude Code on the web through the launcher.

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

### §AR40 The site

roadkeep, Modelado and the other products each have a prerendered English page at
alegauss.github.io/<product>/, built from a site/ workspace in their own repository:
Vite, React 19, TypeScript and Tailwind v4, with the nav, footer, buttons and theme
toggle from @viglet/viglet-design-system/site, the colours from its tokens, and the
prerender and social card from its /vite helpers. Every word lives in src/content.ts,
the route and its metadata in src/routes.ts, and the prerender writes title,
description, canonical and og:url by replace-or-throw.

askround's site follows that layout at /askround/. Its first screen states the pain (you
cannot see what assistants say about your product, and your agent cannot ask them) and
shows a real round report, recorded, not mocked; then the agent-first design with
roadkeep's family, install, and the measured cost.

Done when site/ builds a prerendered page at /askround/ with the design system's chrome,
the README links it, and Lighthouse accessibility scores 100.

### §AR41 site.yml

Modelado's site.yml builds the site on every push that touches site/ and publishes it to
GitHub Pages under /modelado/; a template missing an anchor fails the same build.

askround gets the same workflow: on a push touching site/, npm ci, npm run build as the
gate, and the deploy to /askround/, with the build failing on a missing prerender
anchor.

Done when a push changing content.ts is built by site.yml and live at
alegauss.github.io/askround/.

### §AR42 The docs

roadkeep's site has a docs section (alegauss.github.io/roadkeep/docs/) with pages for
adopting a backlog, what an agent receives in a session, and the reference, so the
README stays a first screen.

askround's site gets the same section: install (plugin at project scope, uvx, pip), a
first session in Claude Code (ask in plain words, what the agent calls), the laws,
prompt sets and leading questions, budget and consent, reading a report and a diff, the
MCP tools with their schemas, the CLI with its JSON and exit codes, and what askround
measures (the APIs, not the apps).

Done when each of those pages exists under /askround/docs/, linked from the README and
the site's nav.

### §AR43 Readable by assistants, measured by itself

The family's sites carry an llms.txt and structured data so assistants can read them;
askround's site must do it best, since its whole subject is what assistants say.

The site ships llms.txt with the product in a paragraph and links to the docs, JSON-LD
for a SoftwareApplication (licence, platforms, price, repository, PyPI), a sitemap and
the social card. askround keeps a prompt set about itself (questions a developer would
ask: track whether ChatGPT recommends my app, an MCP server to ask several LLMs with web
search) and the site shows its latest round, honestly, including when askround is not
named.

Done when llms.txt and the JSON-LD validate, and the site shows a dated round of
askround's own prompt set.
