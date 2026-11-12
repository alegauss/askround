# Improvements

## Block A — The round: one question to every assistant, with web search

### §AR2 Web search on every provider

The app ChatGPT recommended had existed for two weeks. A model answering from its
weights alone could not know it; the assistant found it through web search and linked
its site. A round that does not search measures something no user sees.

Each adapter turns search on with the provider's own tool: OpenAI's Responses API web
search tool, Gemini's grounding with Google Search, Anthropic's web search tool, and
Perplexity's Sonar models, which search by default. The answer keeps the search queries
and sources the provider reports.

Done when every adapter returns an answer with its cited sources for a question about a
product released this month, and a round can be run with search off to compare.

### §AR3 askround doctor

Before proposing a round, the agent had to list environment variables one by one
(OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, PERPLEXITY_API_KEY and others) to
know what could run, taking care not to print a value.

`askround doctor` lists every provider askround knows, whether its key is set (never its
value), the model it would use, whether web search is available on that model, and the
result of one cheap call. It exits non-zero when no provider can run.

Done when doctor reports each provider correctly with keys present, absent and invalid,
and no key ever appears in its output.

### §AR4 Repeated runs and frequency

On 12/11/2026 the question that put Modelado first was asked again in a fresh chat to
tell a pattern from luck. Every answer from a sampled model can change: the order, the
products, the links.

A round runs each question several times per provider (default 3, configurable), in
fresh conversations, and reports for each product how often it appeared and at which
positions, alongside the raw answers.

Done when a round of three runs reports, per provider, the share of runs naming the
product and its positions, and the raw answers stay available.

### §AR5 Record what produced each answer

An API answer is not what a person sees in the ChatGPT or Gemini app: the app adds
memory, personalisation and its own model choice. That gap cannot be closed, only
recorded, so each answer has to say exactly what produced it.

Each stored answer keeps the provider, the exact model id the API reports, the search
tool and its settings, the locale, the temperature, the run number and the timestamp.
Models can be pinned per provider. The README states plainly that askround measures the
APIs, not the apps.

Done when every stored answer carries these fields and a report can group answers by
model id.

### §AR6 Locale and location

One of the tests on 12/11/2026 was asked in Brazilian Portuguese, because the Microsoft
Store showed Brazil among the app's top markets. Search results, and so the
recommendations, depend on the asker's language and country.

A round accepts a language and a country per question, passed to each provider where its
API allows it (OpenAI's web search user location, Gemini's language, Perplexity's search
settings), and records when a provider ignored it.

Done when the same question asked as Brazil and as the United States records the locale
used by each provider, and the report compares the two.

### §AR7 Retries and partial rounds

A round of ten questions, four providers and three runs is 120 calls with web search,
each slow and each able to fail.

Calls are retried with backoff on rate limits and transient errors, with a timeout per
call; a call that still fails is recorded as failed with its error, and the round
completes with what it has. The report shows the failures.

Done when a round with a provider forced to fail still finishes, reports that provider's
failures, and keeps the other answers.

## Block B — Reading the answers: mentions, rank, rivals, citations and claims

### §AR8 Mentions and rank

The analysis needed one fact per answer: is the product there, and in which position of
the recommendation list. It was read by eye from long answers with tables, images and
follow-up questions.

For a target product, defined by its names, aliases and domains, askround finds each
mention and the product's rank in the answer's recommendations, using a structured
extraction pass (a model call with a JSON schema, checked against plain text matching)
so that 'Best fit' in a table and 'my first choice' in prose both count.

Done when, on recorded answers from 12/11/2026, it reports the app as first where it was
first and absent where it was absent.

### §AR9 Competitors named in answers

The generic question on 12/11/2026 recommended Modly first, a rival with thousands of
stars that the product's notes did not mention. It was found by reading.

Every product an answer recommends is extracted with its rank and the reason given, and
a round aggregates them across runs and providers: how often each rival appears, where,
and for which questions.

Done when a round reports the list of rivals with counts and ranks, and the recorded
answers from 12/11/2026 yield Modly at the top of the generic question.

### §AR10 Citations and which page was cited

The answers on 12/11/2026 cited the app's site, its GitHub repository and, wrongly,
other apps' Store pages. Which page an assistant reads is the page whose wording decides
the answer.

Each answer's citations (from the provider's search metadata and from the links in the
text) are stored, and those on the product's own domains are classified (site,
repository, store, docs); third-party pages are counted per rival.

Done when a report shows, per provider, which of the product's pages were cited and how
often.

### §AR11 Claims about the product

On 12/11/2026, the answer that put Modelado first wrote 'Check build' in its CPU-only
column, while a rival that states CPU support plainly got 'Yes'. Comparison tables and
lists of requirements are where assistants make claims a reader acts on.

For the target product, askround extracts the claims an answer makes (requirements,
platforms, price, licence, features, from tables and prose) as attribute and value
pairs, with the sentence they came from.

Done when the recorded answers yield 'CPU only: Check build' and 'NVIDIA GPU required:
No' as claims about the app.

### §AR12 The round report

After each test on 12/11/2026 the agent summarised the answer in a table by hand:
position, what it said, the rivals.

`askround report` prints, for a round, a table of question by provider with the
product's frequency and ranks, the top rivals, the product's cited pages and its claims,
in Markdown for a person and JSON for a pipeline.

Done when one command turns a stored round into that report in both formats.

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
stripped), including the answers from 12/11/2026 as fixtures for the extraction tests; a
separate, opt-in live test checks each adapter against its real API with the smallest
call. CI runs only the recorded tests.

Done when the test suite runs with no key and no network, and the live tests run when
keys are present and are asked for.
