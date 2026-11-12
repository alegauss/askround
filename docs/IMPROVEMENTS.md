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
