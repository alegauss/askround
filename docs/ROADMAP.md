# Roadmap (active backlog)

## Priority

## Block G — Shipping: package, tests and the first screen

## Block H — Agent-first, with roadkeep as the reference

- 📋 **AR36** (deps: AR20 ✅) **An agent asking the same question again the same day pays for the same round twice** — Agents repeat themselves across turns and sessions; a repeated round should cost nothing unless a fresh answer is asked for. → §AR36
- 📋 **AR37** (deps: AR29 ✅, AR31 ✅) **Nothing measures how many tokens each MCP response costs the agent, so outputs grow unnoticed** — roadkeep was born from measuring what its files cost an agent; without a measured budget, each new field makes askround heavier. → §AR37
- 📋 **AR38** (deps: AR24 ✅, AR27 ✅) **askround is not wired into a project the way roadkeep is: one install that every clone and every surface gets** — roadkeep's project-scoped plugin wires every clone with the MCP tools, slash commands and skill; askround should arrive the same way. → §AR38
- 📋 **AR39** (deps: AR1 ✅) **Running askround would mean installing provider SDKs and their dependency trees** — roadkeep is Python 3.11+ with zero runtime dependencies and runs under uvx with no install; askround should start as easily. → §AR39

## Block I — The site at alegauss.github.io/askround

- 📋 **AR40** (deps: —) **askround has no public site: nowhere to see what a round reports, install it or read the docs** — Every product in the family has its page at alegauss.github.io; a developer who hears of askround needs one place that shows a real round. → §AR40
- 📋 **AR41** (deps: AR40) **Nothing builds and deploys the site when it changes** — In the other products a push that changes content.ts is built and live within minutes; a site deployed by hand goes stale. → §AR41
- 📋 **AR42** (deps: AR40) **There are no docs pages: install, a first session in Claude Code, the MCP tools and the CLI reference live nowhere** — roadkeep's docs (install, adopting, in a session) are what lets an agent's user set it up without reading the code. → §AR42
- 📋 **AR43** (deps: AR40, AR16 ✅) **The site is not built to be read by assistants, and askround never measures whether they name askround itself** — A tool that measures how assistants see a product should be readable by them and should measure itself first, publicly. → §AR43

## Done when — AR28

- **pip install askround installs the published package on Windows, macOS and Linux**
  Checked by installing from PyPI into a fresh virtual environment on each system and
  running askround doctor --no-check.

## Non-goals

- **Scraping consumer chat apps** Only the providers' official APIs with web search:
  driving the ChatGPT or Gemini web apps breaks their terms and breaks on every UI
  change. The gap between API and app is documented, not hidden.
- **Writing content to sway assistants** askround measures what assistants say and
  points at the page that lacks a fact; generating text meant to manipulate answers is
  out.
- **Storing API keys** Keys are read from environment variables at run time and never
  written to disk, logs, reports or exported rows.
