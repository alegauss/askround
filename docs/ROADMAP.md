# Roadmap (active backlog)

## Priority

## Block G — Shipping: package, tests and the first screen

## Block H — Agent-first, with roadkeep as the reference

## Block I — The site at alegauss.github.io/askround

## Block J — Found in use: the first real rounds

- 📋 **AR44** (deps: —) **A round's actual cost runs 64% over its estimate, and --max-cost never stops a set that passes it** — On 13/11/2026 a set estimated at $0.83 with a $1.00 cap cost $1.36; a user who approves an estimate must be able to trust the cap. → §AR44
- 📋 **AR45** (deps: —) **A run whose output is redirected on Windows crashes on the report after paying for every answer** — The console's cp1252 cannot encode a character an answer holds (U+2011), so a scheduled or piped run exits 1 though its round is saved. → §AR45
- 📋 **AR46** (deps: —) **report refuses an interrupted set, so its paid answers are read only by finding each question's folder** — A set stopped mid-way keeps its finished rounds, but report needs the set summary written only at the end, and run cannot resume it. → §AR46

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
