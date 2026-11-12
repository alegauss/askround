# Shipped Ledger

## Block A — The round: one question to every assistant, with web search

- ✅ **AR1** **No code exists to send one question to several assistants and keep their answers side by side** — askround ask sends one question to every provider with a key (OpenAI, Gemini, Anthropic) in parallel, prints the answers together and saves each raw response with the date.
- ✅ **AR2** **Providers are called without web search, so an answer cannot name a product newer than the model's training** — Every adapter searches with its provider's own tool and keeps queries and cited sources, with --no-search to compare; OpenAI and Gemini were checked live.
- ✅ **AR3** **Which providers can run depends on keys in the environment, and nothing says which ones are there** — askround doctor lists each provider's key variable (never its value), model, search tool and a free check call, telling rejected keys from missing models.
- ✅ **AR4** **One answer is taken as the answer, though the same question gives a different list on the next run** — A round asks each provider three times by default (--runs) and --product reports per provider the share of runs naming it and its position in each, raw answers kept.

## Block B — Reading the answers: mentions, rank, rivals, citations and claims

## Block C — Trust: checking what the answers say

## Block D — Questions: prompt sets and finding the question that leads to a product

## Block E — Over time: the series, the diff, the cost and the export

## Block F — For agents: an MCP server, a skill and research across assistants

## Block G — Shipping: package, tests and the first screen

## Block H — Agent-first, with roadkeep as the reference

- ✅ **AR30** **No written laws bind askround's design, so the agent-first rules can erode one feature at a time** — askround's six laws open IMPROVEMENTS.md as §0.1, from context is cost to the person sets the money, and the project skill says a rationale names the law it serves.

## Block I — The site at alegauss.github.io/askround

