# Roadmap (active backlog)

## Block A — The round: one question to every assistant, with web search

- 📋 **AR2** (deps: AR1 ✅) **Providers are called without web search, so an answer cannot name a product newer than the model's training** — Assistants recommend apps through search with links; a plain completion never names a two-week-old app that ChatGPT sends people to. → §AR2
- 📋 **AR3** (deps: AR1 ✅) **Which providers can run depends on keys in the environment, and nothing says which ones are there** — On 12/11/2026 the agent checked environment variables by hand to learn that OpenAI and Gemini were usable and Anthropic was not. → §AR3
- 📋 **AR4** (deps: AR1 ✅) **One answer is taken as the answer, though the same question gives a different list on the next run** — Assistants vary run to run, so 'it named the app first' means nothing until it is 'first in 3 of 3 runs'. → §AR4
- 📋 **AR5** (deps: AR2) **The model, tools and settings behind an answer are not recorded, so a change cannot be told from drift** — Providers update models and search silently; a product dropping out of answers must be traceable to a new model or to the product itself. → §AR5
- 📋 **AR6** (deps: AR2) **A question cannot be asked as someone in a given country and language would ask it** — A Portuguese question about running on the CPU also put the app first; country and language change which products search finds. → §AR6
- 📋 **AR7** (deps: AR1 ✅) **A rate limit, timeout or provider error aborts the round instead of being retried and reported** — A round makes dozens of calls across providers, and one failure should cost one answer, not the whole round. → §AR7

## Block B — Reading the answers: mentions, rank, rivals, citations and claims

- 📋 **AR8** (deps: AR4) **Whether a product is named, and in which position, is read by eye in each answer** — On 12/11/2026 every answer was read in full to find where the app ranked; at three runs and four providers that does not scale. → §AR8
- 📋 **AR9** (deps: AR8) **The rivals an answer recommends are not listed, so a competitor like Modly is found only by reading** — The strongest competitor of the app surfaced only because the agent read a pasted answer; it was missing from the product's own notes. → §AR9
- 📋 **AR10** (deps: AR8) **The links an answer cites are not collected, so which page brought the product (site, repo, store) is unknown** — Knowing that an assistant cites the product's site and not its GitHub or Store page tells which page to improve first. → §AR10
- 📋 **AR11** (deps: AR8) **What an answer claims about the product is not captured, such as 'CPU only: Check build' in a table** — The answer that ranked the app first also doubted its CPU support, a claim that decides a reader's choice and that the product can fix. → §AR11
- 📋 **AR12** (deps: AR8) **There is no short report of a round; reading it means opening every raw answer** — The person deciding needs one table: question by provider, with rank, frequency and the rivals around the product. → §AR12

## Block C — Trust: checking what the answers say

- 📋 **AR13** (deps: AR9) **A product an answer names may not exist, like two Windows apps no search could find** — An answer recommended 'Presidium Shape Studio' and 'MeshForge3D' as apps; research could not find either, so an invented rival could steer a decision. → §AR13
- 📋 **AR14** (deps: AR10) **A cited link or picture may belong to another product, like a Store page of a different app shown for Modelado** — A reader who clicks the picture beside the recommended app can install a rival; the product owner never learns it happened. → §AR14
- 📋 **AR15** (deps: AR11) **Claims about the product are not checked against what is true, so a wrong 'needs NVIDIA' goes unnoticed** — The fix for a wrong claim is a sentence on the page the assistant reads; askround can say which claim is wrong and which page lacks it. → §AR15

## Block D — Questions: prompt sets and finding the question that leads to a product

- 📋 **AR16** (deps: AR1 ✅) **Questions live in chat history; there is no prompt set per product to run again next week** — The four questions that explained the app's audience were typed once and would have to be retyped to see whether anything changed. → §AR16
- 📋 **AR17** (deps: AR8, AR16) **Finding which question leads an assistant to a product took four manual tries** — The generic question never named the app; only the 'without NVIDIA' one did, which explained its audience and set its messaging. → §AR17
- 📋 **AR18** (deps: AR16) **Nothing warns when a question names the product it tests, which makes its answer worthless** — A question that mentions the product, or its domain, steers the assistant toward it and measures nothing. → §AR18
- 📋 **AR19** (deps: AR16) **A question could carry personal data, an email or a person's name, to every provider at once** — One round sends the same text to four companies; a slip in a prompt is a leak to all of them. → §AR19

## Block E — Over time: the series, the diff, the cost and the export

- 📋 **AR20** (deps: AR8) **Rounds are not kept as a series, so a product entering or leaving the answers goes unnoticed** — The app's audience moved on a given day; only a weekly series shows when an assistant started or stopped naming it. → §AR20
- 📋 **AR21** (deps: AR9, AR20) **Nothing compares a round with the previous one: a new rival, a rank lost, a product dropped** — The change between two rounds is what someone needs to act on, and the full report hides it. → §AR21
- 📋 **AR22** (deps: AR2) **The cost of a round is unknown before it runs, and web search is billed apart from tokens** — A round is dozens of searched calls; without an estimate and a cap a weekly habit can cost more than it is worth. → §AR22
- 📋 **AR23** (deps: AR20) **A round cannot be exported to a dashboard or another project's data** — The visibility work that needs it keeps daily numbers per product; askround's rows should land there without a manual copy. → §AR23

## Block F — For agents: an MCP server, a skill and research across assistants

- 📋 **AR24** (deps: AR1 ✅) **An agent in Claude Code cannot ask other assistants mid-analysis; it has to stop and ask the user** — On 12/11/2026 the analysis paused four times for the user to run a question in ChatGPT; an MCP tool lets the agent run it itself. → §AR24
- 📋 **AR25** (deps: AR24) **Researching a question across assistants means reading each answer and merging the sources by hand** — The same session researched model licences and competitors; asking several assistants with search and merging their sources would have cut that work. → §AR25
- 📋 **AR26** (deps: AR25) **Disagreements between assistants on a fact, such as a model's licence, are not flagged for a check at the source** — Where assistants disagree is where a decision is at risk; a third-party page on 12/11/2026 had called an Apache-2.0 model non-commercial. → §AR26
- 📋 **AR27** (deps: AR24) **No Claude Code skill tells an agent when to use askround instead of asking the user to test a prompt** — A tool an agent does not know to reach for is a tool it does not use; the skill is what turns the MCP server into a habit. → §AR27

## Block G — Shipping: package, tests and the first screen

- 📋 **AR28** (deps: AR1 ✅) **askround cannot be installed: there is no package, no release and no README first screen** — Someone with the same pain needs pip install askround and a first screen that says what a round tells them. → §AR28
- 📋 **AR29** (deps: AR1 ✅) **Tests would call live APIs, costing money and breaking on every provider change** — An adapter test that pays for a search on every run is skipped, and then the adapters rot. → §AR29

## Non-goals

- **Scraping consumer chat apps** Only the providers' official APIs with web search:
  driving the ChatGPT or Gemini web apps breaks their terms and breaks on every UI
  change. The gap between API and app is documented, not hidden.
- **Writing content to sway assistants** askround measures what assistants say and
  points at the page that lacks a fact; generating text meant to manipulate answers is
  out.
- **Storing API keys** Keys are read from environment variables at run time and never
  written to disk, logs, reports or exported rows.
