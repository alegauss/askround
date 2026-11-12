---
description: Ask the assistants a question with web search, and read whether a product is named
argument-hint: "<question> [product]"
allowed-tools: mcp__askround__askround_ask, mcp__plugin_askround_askround__askround_ask, mcp__askround__askround_answer, mcp__plugin_askround_askround__askround_answer, mcp__askround__askround_doctor, mcp__plugin_askround_askround__askround_doctor
---

Ask this across the assistants, as a person who does not know the product would: $ARGUMENTS

Use `askround_ask` (the tool from the askround MCP server). When the arguments name a
product, pass it as `products` and set `extract: true`; never put the product's name or
domain in the question itself, askround refuses that. Start with `runs: 1` unless the user
asked for more, and give it `max_cost` when the user has not agreed to a price.

If the call is refused, report the codes and the fix each one names; do not rephrase the
question to get around a refusal the user should decide on. If no provider can run, call
`askround_doctor` and say which key variable each one needs (names, never values).

Report from the brief: where the product is named and at which positions, the rivals, the
claims with the answers they came from, what the round cost, and that askround measures
the APIs, not the chat apps. Read an answer with `askround_answer` only to check a fact.
