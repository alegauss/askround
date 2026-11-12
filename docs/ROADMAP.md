# Roadmap (active backlog)

## Priority

## Block C — Trust: checking what the answers say

- 📋 **AR13** (deps: AR9 ✅) **A product an answer names may not exist, like two Windows apps no search could find** — An answer recommended 'Presidium Shape Studio' and 'MeshForge3D' as apps; research could not find either, so an invented rival could steer a decision. → §AR13
- 📋 **AR14** (deps: AR10 ✅) **A cited link or picture may belong to another product, like a Store page of a different app shown for Modelado** — A reader who clicks the picture beside the recommended app can install a rival; the product owner never learns it happened. → §AR14
- 📋 **AR15** (deps: AR11 ✅) **Claims about the product are not checked against what is true, so a wrong 'needs NVIDIA' goes unnoticed** — The fix for a wrong claim is a sentence on the page the assistant reads; askround can say which claim is wrong and which page lacks it. → §AR15

## Block D — Questions: prompt sets and finding the question that leads to a product

- 📋 **AR16** (deps: AR1 ✅) **Questions live in chat history; there is no prompt set per product to run again next week** — The four questions that explained the app's audience were typed once and would have to be retyped to see whether anything changed. → §AR16
- 📋 **AR17** (deps: AR8 ✅, AR16) **Finding which question leads an assistant to a product took four manual tries** — The generic question never named the app; only the 'without NVIDIA' one did, which explained its audience and set its messaging. → §AR17
- 📋 **AR18** (deps: AR16) **Nothing warns when a question names the product it tests, which makes its answer worthless** — A question that mentions the product, or its domain, steers the assistant toward it and measures nothing. → §AR18
- 📋 **AR19** (deps: AR16) **A question could carry personal data, an email or a person's name, to every provider at once** — One round sends the same text to four companies; a slip in a prompt is a leak to all of them. → §AR19

## Block E — Over time: the series, the diff, the cost and the export

- 📋 **AR20** (deps: AR8 ✅) **Rounds are not kept as a series, so a product entering or leaving the answers goes unnoticed** — The app's audience moved on a given day; only a weekly series shows when an assistant started or stopped naming it. → §AR20
- 📋 **AR21** (deps: AR9 ✅, AR20) **Nothing compares a round with the previous one: a new rival, a rank lost, a product dropped** — The change between two rounds is what someone needs to act on, and the full report hides it. → §AR21
- 📋 **AR22** (deps: AR2 ✅) **The cost of a round is unknown before it runs, and web search is billed apart from tokens** — A round is dozens of searched calls; without an estimate and a cap a weekly habit can cost more than it is worth. → §AR22
- 📋 **AR23** (deps: AR20) **A round cannot be exported to a dashboard or another project's data** — The visibility work that needs it keeps daily numbers per product; askround's rows should land there without a manual copy. → §AR23

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
- 📋 **AR33** (deps: AR18, AR19, AR22, AR24) **A bad round is discovered after it is paid for: a leading question, personal data or a cost over budget** — roadkeep refuses an over-long line in the MCP schema before the prose exists; askround must refuse a bad round before the first paid call. → §AR33
- 📋 **AR34** (deps: AR22, AR24) **An agent could spend the user's API money on rounds without the user ever agreeing to the amount** — A tool an agent can call in a loop needs a spending limit the person sets, and a stop that asks before going past it. → §AR34
- 📋 **AR35** (deps: AR24) **A round takes minutes of searched calls, longer than an MCP call should block the agent** — An agent waiting on one tool call for minutes stalls its session, or times out and loses a round it already paid for. → §AR35
- 📋 **AR36** (deps: AR20) **An agent asking the same question again the same day pays for the same round twice** — Agents repeat themselves across turns and sessions; a repeated round should cost nothing unless a fresh answer is asked for. → §AR36
- 📋 **AR37** (deps: AR29, AR31) **Nothing measures how many tokens each MCP response costs the agent, so outputs grow unnoticed** — roadkeep was born from measuring what its files cost an agent; without a measured budget, each new field makes askround heavier. → §AR37
- 📋 **AR38** (deps: AR24, AR27) **askround is not wired into a project the way roadkeep is: one install that every clone and every surface gets** — roadkeep's project-scoped plugin wires every clone with the MCP tools, slash commands and skill; askround should arrive the same way. → §AR38
- 📋 **AR39** (deps: AR1 ✅) **Running askround would mean installing provider SDKs and their dependency trees** — roadkeep is Python 3.11+ with zero runtime dependencies and runs under uvx with no install; askround should start as easily. → §AR39

## Block I — The site at alegauss.github.io/askround

- 📋 **AR40** (deps: —) **askround has no public site: nowhere to see what a round reports, install it or read the docs** — Every product in the family has its page at alegauss.github.io; a developer who hears of askround needs one place that shows a real round. → §AR40
- 📋 **AR41** (deps: AR40) **Nothing builds and deploys the site when it changes** — In the other products a push that changes content.ts is built and live within minutes; a site deployed by hand goes stale. → §AR41
- 📋 **AR42** (deps: AR40) **There are no docs pages: install, a first session in Claude Code, the MCP tools and the CLI reference live nowhere** — roadkeep's docs (install, adopting, in a session) are what lets an agent's user set it up without reading the code. → §AR42
- 📋 **AR43** (deps: AR40, AR16) **The site is not built to be read by assistants, and askround never measures whether they name askround itself** — A tool that measures how assistants see a product should be readable by them and should measure itself first, publicly. → §AR43

## Non-goals

- **Scraping consumer chat apps** Only the providers' official APIs with web search:
  driving the ChatGPT or Gemini web apps breaks their terms and breaks on every UI
  change. The gap between API and app is documented, not hidden.
- **Writing content to sway assistants** askround measures what assistants say and
  points at the page that lacks a fact; generating text meant to manipulate answers is
  out.
- **Storing API keys** Keys are read from environment variables at run time and never
  written to disk, logs, reports or exported rows.
