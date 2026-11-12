---
name: askround
description: "Ask other AI assistants (ChatGPT/OpenAI, Gemini, Claude, Perplexity) a question yourself, with web search, instead of asking the user to type it into a chat app and paste the answer back. Use when the task needs to know whether assistants recommend a product, app, library or site (\"do assistants recommend my app?\", \"why does ChatGPT send people to us?\", \"who are our rivals in AI answers?\"), which question leads an assistant to it, what they claim about it and whether that is true, which of its pages they cite, how that changes week to week; and for research across assistants (licences, competitors, facts) where agreement and disagreement matter. Trigger words: ChatGPT recommends, AI visibility, LLM visibility, GEO, generative engine optimization, assistant answers, ask ChatGPT, ask Gemini, askround."
---

# askround: ask the assistants yourself

askround sends one question to several AI assistants through their APIs, with web search
on, several times each, and reads the answers: whether a product is named, at which
position, what is claimed about it, which pages are cited, which rivals surround it. Do
not ask the user to try a prompt in ChatGPT; run it.

Use the MCP tools when they are listed (`askround_*`); otherwise the CLI, `askround`.
Start with `askround_doctor` (`askround doctor`) to see which providers have a key.

## Which tool

| The question | Tool | CLI |
| --- | --- | --- |
| Do assistants recommend X? Where? | `askround_ask` with `products: ["X,x.com"]`, `extract: true` | `askround ask "..." --product "X,x.com" --extract` |
| The text of one answer | `askround_answer` | `askround report` then the round's `round.json` |
| The same questions again, every week | `askround_run` on a product file | `askround run x.toml` |
| Which wording leads them to X? | - | `askround discover x.toml --seed "..."` |
| What changed since last time? | `askround_diff` | `askround diff` |
| A research question (licences, facts) | `askround_research` | `askround research "..."` |

## Ask as a person would

- **Never name the product in the question** (or its domain, or its own wording): the
  answer would measure nothing, and askround refuses it. To ask about the product on
  purpose, mark it a brand question (`--brand`); it is reported apart.
- **No personal data**: one round sends the text to every provider. askround refuses an
  email address, a phone number, a CPF or a key in a question.
- Ask the way the product's audience asks: their constraint ("without an NVIDIA GPU"),
  their use case, their language (`locales: ["BR:pt-BR"]`, and write the question in it).

## Money

Every round has a cost the user pays. askround prints an estimate and refuses a round
above `max_cost` / `ASKROUND_MAX_COST` before any call. Keep runs low while exploring
(`runs: 1`), and set `max_cost` on anything the user has not agreed to; tell the user
what a round cost (the report has it).

## Reading what comes back

- A product is "named in 2/3 runs, positions #1, #3, -": answers vary, never trust one.
- Positions marked `*` were read by the extraction pass ("Best fit" in a table counts).
- Claims are quoted from the answer; a fact gap is a claim that contradicts or doubts the
  product file's facts, with the page that should say it plainly.
- Research claims are ranked by how many assistants agree; agreement is not proof. Read
  the disagreements first, and settle them at the primary source.
- askround measures the APIs, not the chat apps: say so when you report its numbers.

Read one answer's text only when the report is not enough: context is cost.
