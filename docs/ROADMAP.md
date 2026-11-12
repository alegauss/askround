# Roadmap (active backlog)

## Priority

## Block G — Shipping: package, tests and the first screen

## Block H — Agent-first, with roadkeep as the reference

## Block I — The site at alegauss.github.io/askround

- 📋 **AR40** (deps: —) **askround has no public site: nowhere to see what a round reports, install it or read the docs** — Every product in the family has its page at alegauss.github.io; a developer who hears of askround needs one place that shows a real round. → §AR40
- 📋 **AR41** (deps: AR40) **Nothing builds and deploys the site when it changes** — In the other products a push that changes content.ts is built and live within minutes; a site deployed by hand goes stale. → §AR41
- 📋 **AR42** (deps: AR40) **There are no docs pages: install, a first session in Claude Code, the MCP tools and the CLI reference live nowhere** — roadkeep's docs (install, adopting, in a session) are what lets an agent's user set it up without reading the code. → §AR42
- 📋 **AR43** (deps: AR40, AR16 ✅) **The site is not built to be read by assistants, and askround never measures whether they name askround itself** — A tool that measures how assistants see a product should be readable by them and should measure itself first, publicly. → §AR43

## Done when — AR28

- **pip install askround installs the published package on Windows, macOS and Linux**
  Checked by installing from PyPI into a fresh virtual environment on each system and
  running askround doctor --no-check.

## Done when — AR39

- **pip install askround installs nothing else** tests/test_dependencies.py fails on a
  third-party import or a declared dependency; a clean venv held only askround and pip.
- **uvx askround doctor runs on a clean machine** Run uvx askround doctor on a machine
  with uv and no askround, once the package is on PyPI.

## Non-goals

- **Scraping consumer chat apps** Only the providers' official APIs with web search:
  driving the ChatGPT or Gemini web apps breaks their terms and breaks on every UI
  change. The gap between API and app is documented, not hidden.
- **Writing content to sway assistants** askround measures what assistants say and
  points at the page that lacks a fact; generating text meant to manipulate answers is
  out.
- **Storing API keys** Keys are read from environment variables at run time and never
  written to disk, logs, reports or exported rows.
