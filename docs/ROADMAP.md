# Roadmap (active backlog)

## Priority

## Block F — For agents: an MCP server, a skill and research across assistants

- 📋 **AR24** (deps: AR1 ✅) **An agent in Claude Code cannot ask other assistants mid-analysis; it has to stop and ask the user** — On 12/11/2026 the analysis paused four times for the user to run a question in ChatGPT; an MCP tool lets the agent run it itself. → §AR24
- 📋 **AR25** (deps: AR24) **Researching a question across assistants means reading each answer and merging the sources by hand** — The same session researched model licences and competitors; asking several assistants with search and merging their sources would have cut that work. → §AR25
- 📋 **AR26** (deps: AR25) **Disagreements between assistants on a fact, such as a model's licence, are not flagged for a check at the source** — Where assistants disagree is where a decision is at risk; a third-party page on 12/11/2026 had called an Apache-2.0 model non-commercial. → §AR26
- 📋 **AR27** (deps: AR24) **No Claude Code skill tells an agent when to use askround instead of asking the user to test a prompt** — A tool an agent does not know to reach for is a tool it does not use; the skill is what turns the MCP server into a habit. → §AR27

## Block G — Shipping: package, tests and the first screen

- 📋 **AR28** (deps: AR1 ✅) **askround cannot be installed: there is no package, no release and no README first screen** — Someone with the same pain needs pip install askround and a first screen that says what a round tells them. → §AR28
- 📋 **AR29** (deps: AR1 ✅) **Tests would call live APIs, costing money and breaking on every provider change** — An adapter test that pays for a search on every run is skipped, and then the adapters rot. → §AR29

## Block H — Agent-first, with roadkeep as the reference

- 📋 **AR31** (deps: AR12 ✅, AR24) **A round hands the agent every raw answer, so one check of a product spends tens of thousands of tokens of context** — roadkeep's answer to context cost is 'ask instead of read'; askround returns the extracted result and one raw answer only when asked. → §AR31
- 📋 **AR32** (deps: AR12 ✅) **Output is meant for a person to read, with no stable schema an agent or a script can rely on** — Every roadkeep command takes --json and says which file and line an answer came from; askround's agents need the same contract. → §AR32
- 📋 **AR33** (deps: AR18 ✅, AR19 ✅, AR22 ✅, AR24) **A bad round is discovered after it is paid for: a leading question, personal data or a cost over budget** — roadkeep refuses an over-long line in the MCP schema before the prose exists; askround must refuse a bad round before the first paid call. → §AR33
- 📋 **AR34** (deps: AR22 ✅, AR24) **An agent could spend the user's API money on rounds without the user ever agreeing to the amount** — A tool an agent can call in a loop needs a spending limit the person sets, and a stop that asks before going past it. → §AR34
- 📋 **AR35** (deps: AR24) **A round takes minutes of searched calls, longer than an MCP call should block the agent** — An agent waiting on one tool call for minutes stalls its session, or times out and loses a round it already paid for. → §AR35
- 📋 **AR36** (deps: AR20 ✅) **An agent asking the same question again the same day pays for the same round twice** — Agents repeat themselves across turns and sessions; a repeated round should cost nothing unless a fresh answer is asked for. → §AR36
- 📋 **AR37** (deps: AR29, AR31) **Nothing measures how many tokens each MCP response costs the agent, so outputs grow unnoticed** — roadkeep was born from measuring what its files cost an agent; without a measured budget, each new field makes askround heavier. → §AR37
- 📋 **AR38** (deps: AR24, AR27) **askround is not wired into a project the way roadkeep is: one install that every clone and every surface gets** — roadkeep's project-scoped plugin wires every clone with the MCP tools, slash commands and skill; askround should arrive the same way. → §AR38
- 📋 **AR39** (deps: AR1 ✅) **Running askround would mean installing provider SDKs and their dependency trees** — roadkeep is Python 3.11+ with zero runtime dependencies and runs under uvx with no install; askround should start as easily. → §AR39

## Block I — The site at alegauss.github.io/askround

- 📋 **AR40** (deps: —) **askround has no public site: nowhere to see what a round reports, install it or read the docs** — Every product in the family has its page at alegauss.github.io; a developer who hears of askround needs one place that shows a real round. → §AR40
- 📋 **AR41** (deps: AR40) **Nothing builds and deploys the site when it changes** — In the other products a push that changes content.ts is built and live within minutes; a site deployed by hand goes stale. → §AR41
- 📋 **AR42** (deps: AR40) **There are no docs pages: install, a first session in Claude Code, the MCP tools and the CLI reference live nowhere** — roadkeep's docs (install, adopting, in a session) are what lets an agent's user set it up without reading the code. → §AR42
- 📋 **AR43** (deps: AR40, AR16 ✅) **The site is not built to be read by assistants, and askround never measures whether they name askround itself** — A tool that measures how assistants see a product should be readable by them and should measure itself first, publicly. → §AR43

## Non-goals

- **Scraping consumer chat apps** Only the providers' official APIs with web search:
  driving the ChatGPT or Gemini web apps breaks their terms and breaks on every UI
  change. The gap between API and app is documented, not hidden.
- **Writing content to sway assistants** askround measures what assistants say and
  points at the page that lacks a fact; generating text meant to manipulate answers is
  out.
- **Storing API keys** Keys are read from environment variables at run time and never
  written to disk, logs, reports or exported rows.
