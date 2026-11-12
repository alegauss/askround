---
description: Run a product file's prompt set, every question across the assistants
argument-hint: "<product.toml>"
allowed-tools: mcp__askround__askround_run, mcp__plugin_askround_askround__askround_run, mcp__askround__askround_job, mcp__plugin_askround_askround__askround_job
---

Run the prompt set in this product file: $ARGUMENTS

Use `askround_run` with `file` set to that path. A set takes minutes, so pass
`background: true` and read it with `askround_job` until it is done, working on something
else meanwhile. Give it `max_cost` when the user has not agreed to a price.

Report one line per question: its purpose, whether the product was named and where, and
the leading rival; then the cost. Point at the questions where the product is missing,
since those are the ones worth acting on.
