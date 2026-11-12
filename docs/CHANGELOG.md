# Shipped Ledger

## Block A — The round: one question to every assistant, with web search

- ✅ **AR1** **No code exists to send one question to several assistants and keep their answers side by side** — askround ask sends one question to every provider with a key (OpenAI, Gemini, Anthropic) in parallel, prints the answers together and saves each raw response with the date.
- ✅ **AR2** **Providers are called without web search, so an answer cannot name a product newer than the model's training** — Every adapter searches with its provider's own tool and keeps queries and cited sources, with --no-search to compare; OpenAI and Gemini were checked live.
- ✅ **AR3** **Which providers can run depends on keys in the environment, and nothing says which ones are there** — askround doctor lists each provider's key variable (never its value), model, search tool and a free check call, telling rejected keys from missing models.
- ✅ **AR4** **One answer is taken as the answer, though the same question gives a different list on the next run** — A round asks each provider three times by default (--runs) and --product reports per provider the share of runs naming it and its position in each, raw answers kept.
- ✅ **AR5** **The model, tools and settings behind an answer are not recorded, so a change cannot be told from drift** — Every answer records the requested and served model id, search tool, temperature, locale, settings, run and time; --model pins a model and frequency groups by served model.
- ✅ **AR6** **A question cannot be asked as someone in a given country and language would ask it** — --locale COUNTRY:LANG asks each provider as that locale through its search settings, records what its API ignored, and repeated locales are compared side by side.
- ✅ **AR7** **A rate limit, timeout or provider error aborts the round instead of being retried and reported** — Rate limits, server errors and timeouts are retried with backoff and Retry-After; a call that still fails is recorded with its attempts and the round finishes, listing failures.

## Block B — Reading the answers: mentions, rank, rivals, citations and claims

- ✅ **AR8** **Whether a product is named, and in which position, is read by eye in each answer** — --extract lists each answer's recommendations in order with quotes, checked against its text, so a product ranks by "Best fit" or prose; live and synthetic answers checked, 12/11 originals not kept.
- ✅ **AR9** **The rivals an answer recommends are not listed, so a competitor like Modly is found only by reading** — With --extract a round lists every rival the answers recommend, with answer counts, ranks, providers and a quote; on 12/11 Modly led, but a live round today ranks it lower.
- ✅ **AR10** **The links an answer cites are not collected, so which page brought the product (site, repo, store) is unknown** — Each answer's cited pages are normalised; given its domains, a product's cited pages are counted per provider by kind, and third-party domains and rivals' pages are counted too.
- ✅ **AR11** **What an answer claims about the product is not captured, such as 'CPU only: Check build' in a table** — With --extract each answer's claims about every product (table cells and prose) are read as attribute and value with a verified quote, and a product's claims are aggregated per provider.
- ✅ **AR12** **There is no short report of a round; reading it means opening every raw answer** — askround report turns a stored round (the latest by default) into one Markdown or JSON report: frequency and ranks per provider, claims, cited pages and rivals, without the answers' text.

## Block C — Trust: checking what the answers say

- ✅ **AR13** **A product an answer names may not exist, like two Windows apps no search could find** — askround lookup and --check-rivals check a rival on GitHub, then a searched call; both 12/11 'invented' names exist (design superseded: they exist).
- ✅ **AR14** **A cited link or picture may belong to another product, like a Store page of a different app shown for Modelado** — --check-links follows each link and image an answer gives beside a product and flags those landing on another product's page or broken; Modelado's real Store, site and repo pass.
- ✅ **AR15** **Claims about the product are not checked against what is true, so a wrong 'needs NVIDIA' goes unnoticed** — A product file holds a product's facts and pages; with --extract the answers' claims are judged against them, and a contradicted or doubted fact is reported with the page that should say it.

## Block D — Questions: prompt sets and finding the question that leads to a product

- ✅ **AR16** **Questions live in chat history; there is no prompt set per product to run again next week** — A product file's [[question]] entries form a prompt set; askround run asks them all as one set with a question-by-provider table, and examples/modelado.toml holds the four 12/11 questions.
- ✅ **AR17** **Finding which question leads an assistant to a product took four manual tries** — askround discover writes variants of a seed that never name the product, runs them and ranks them by rank and frequency; a 1-run live test ranked the seed first.
- ✅ **AR18** **Nothing warns when a question names the product it tests, which makes its answer worthless** — A question naming the product, an alias, a place or a listed phrase is refused before any call; a brand question (--brand, brand = true) runs, marked and reported apart.
- ✅ **AR19** **A question could carry personal data, an email or a person's name, to every provider at once** — Every question, seed, variant and lookup is scanned for emails, phones, CPFs, IPs, API keys and the person's private names, and stops before any call naming what it found.

## Block E — Over time: the series, the diff, the cost and the export

- ✅ **AR20** **Rounds are not kept as a series, so a product entering or leaving the answers goes unnoticed** — Every saved round appends a row per answer to series.jsonl, rebuildable from the rounds; askround series gives a product's share per week, day or month per provider.
- ✅ **AR21** **Nothing compares a round with the previous one: a new rival, a rank lost, a product dropped** — askround diff compares two rounds or set runs per question and provider, naming share and rank changes, rivals and cited pages that appeared or left, and claims made or dropped.
- ✅ **AR22** **The cost of a round is unknown before it runs, and web search is billed apart from tokens** — A run prints its estimate from a dated price table, refuses one above --max-cost before any call, and reports the actual cost per provider from each API's usage.
- ✅ **AR23** **A round cannot be exported to a dashboard or another project's data** — askround export writes a product's rows from the series per day, provider and question as CSV, JSON or a daily.json shape, and the README shows a weekly schedule on Windows and cron.

## Block F — For agents: an MCP server, a skill and research across assistants

- ✅ **AR24** **An agent in Claude Code cannot ask other assistants mid-analysis; it has to stop and ask the user** — askround mcp serves ask, answer, run, report, diff and doctor over stdio with every refusal and the cost cap; a stdio client asked two providers and read an answer.
- ✅ **AR25** **Researching a question across assistants means reading each answer and merging the sources by hand** — askround research asks every provider with search, merges the answers' verified statements into claims ranked by provider support, with passages and sources primary first; also an MCP tool.
- ✅ **AR26** **Disagreements between assistants on a fact, such as a model's licence, are not flagged for a check at the source** — Research mode reports where the assistants disagree on a fact first, with both sides, their passages and the primary sources to settle it; one provider's own sources are not read.
- ✅ **AR27** **No Claude Code skill tells an agent when to use askround instead of asking the user to test a prompt** — A skill tells an agent when to run askround itself (visibility, discovery, research), how to ask neutrally and within budget; a validated plugin installs it with the MCP server.

## Block G — Shipping: package, tests and the first screen

## Block H — Agent-first, with roadkeep as the reference

- ✅ **AR30** **No written laws bind askround's design, so the agent-first rules can erode one feature at a time** — askround's six laws open IMPROVEMENTS.md as §0.1, from context is cost to the person sets the money, and the project skill says a rationale names the law it serves.

## Block I — The site at alegauss.github.io/askround

