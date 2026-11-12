# askround

Ask several AI assistants the same question and keep their answers side by side.

**askround measures the APIs, not the apps.** An answer from the OpenAI, Gemini,
Anthropic or Perplexity API, with web search on, is close to what their chat apps say
but is not the same page: the apps add memory, personalisation and their own choice of
model. askround cannot close that gap, so it records exactly what produced each answer
(the model asked for and the model that answered, the search tool, the settings, the
time) and every report is about the API.

```
pip install -e .
askround ask "What is the best free app to turn a photo into a 3D model on Windows?"
```

Every provider whose API key is in the environment is asked in parallel:
`OPENAI_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), `ANTHROPIC_API_KEY` and
`PERPLEXITY_API_KEY`. askround reads the keys at call time and never stores them.
`askround doctor` lists which providers can run here: the key variable (never its
value), the model, the search tool and a free check call; `--no-check` makes no call.

Web search is on, through each provider's own search tool, because that is how
assistants find and recommend products. Each answer is printed with the sources it
cited. `--no-search` asks the same question without search, to compare.

Each round is saved under `.askround/rounds/<date>/<time>-<question>/` (change it with
`--out` or `ASKROUND_DIR`): `round.json` holds the question and each provider's answer,
search queries and sources, and `<provider>-<run>.json` the raw response as the provider
sent it. Assistants answer differently from one run to the next, so a product is
reported as "named in 2/3 runs, positions #1, #3, -", never from a single answer.

| Option              | What it does                                        |
| ------------------- | --------------------------------------------------- |
| `--provider NAME`   | ask only this provider (`openai`, `gemini`, `anthropic`, `perplexity`), repeatable |
| `--model PROVIDER=MODEL` | pin the model one provider uses, e.g. `openai=gpt-5-2025-08-07`, repeatable |
| `--no-search`       | ask without web search                              |
| `--runs N`          | ask each provider N times, in fresh conversations (default 3) |
| `--product NAME[,ALIAS...]` | report how many runs named the product and its position in each, repeatable |
| `--extract [PROVIDER]` | read each answer's recommendations in order with a model (one extra call per answer), so "Best fit" in a table or "my first choice" in prose ranks the product first |
| `--locale COUNTRY[:LANG]` | ask as someone in this country, e.g. `BR:pt-BR`; repeat to compare countries side by side |

Without `--extract`, a product's position is read from the answer's text: its place
among the top-level list items, numbered headings and table rows. With it, a small model
(gpt-5-mini, gemini-2.5-flash or claude-haiku-5-5, whichever has a key; override with
`ASKROUND_EXTRACT_MODEL`) lists what the answer recommends in its own order, each with a
quote. The text stays the check: a product counts as named only if its name is in the
answer, and a quote not found in the answer is marked `(?)`. Positions ranked this way
show a `*`.

Give the product's own places among its names, anything with a dot: a domain or a URL
prefix (`--product "Modelado,alegauss.github.io/modelado,github.com/alegauss/modelado"`).
The report then says, per provider, how many answers cited one of its pages and which
kind (site, repository, store, docs), and `round.json` lists every page and the
third-party domains cited. Tracking parameters are dropped; Gemini's redirect links are
counted by the domain in their title.

`--check-links` follows every link an answer writes beside the product's name (in its
table row or list item, or close to it in prose), images included, and flags those that
land on someone else's page, such as another app's Store page shown for yours, or that
are broken. A page counts as the product's when it is on one of its places or its
title names it.

With `--extract`, the report also lists what the answers claim about the product, from
tables and prose: `CPU only: Check build`, `Cost: Free, open-source`, each with the
providers that said it and the passage it came from. A claim whose quote is not in the
answer is counted apart and never shown as a finding.

With `--extract`, the report also lists the rivals: every other product the answers
recommend, with how many answers named it, its rank in each and which providers did
(the first ten in the report, all of them in `round.json`, each with the quote that
recommends it).

Each API takes a different part of a locale, and only for its search: OpenAI,
Anthropic and Perplexity an approximate country, Gemini a language. What a provider
cannot take is recorded on the answer and shown as "ignored by the API". Write the
question in the language you are testing: that is still the strongest signal.
| `--out DIR`         | where the round is saved                            |
| `--json`            | print the round as JSON                             |

A rate limit, a server error, a timeout or a dropped connection is retried up to three
times with backoff (honouring `Retry-After`); a rejected key or a missing model is not.
An answer that still fails is recorded with its error, the rest of the round carries
on, and the report lists the failures at the end.

The model per provider is overridden with `ASKROUND_OPENAI_MODEL`,
`ASKROUND_GEMINI_MODEL`, `ASKROUND_ANTHROPIC_MODEL` and `ASKROUND_PERPLEXITY_MODEL`.

## Does a recommended product exist?

```
askround lookup "MeshForge3D" "Modly" --context "a Windows photo-to-3D app"
askround ask "..." --extract --check-rivals     # the top 10 rivals of a round
```

Each name is looked up on GitHub first (free; a repository of that name with at least
10 stars), then with one searched call on OpenAI, Anthropic or Gemini, which answers
found, ambiguous or not found with the page. A "found" whose page is not among the
pages that search returned is downgraded to ambiguous. `--no-web` keeps it to GitHub.
The report marks each checked rival, and names the ones found nowhere.

## The report

```
askround report                     # the latest round, as Markdown
askround report <round dir> --json  # one round, as JSON for a pipeline
askround report --product Blender   # the same round, read for another product
```

`report` reads a stored round back and sums it up: for each product, a table of
provider by share of runs and positions, what the answers claim about it, which of its
pages they cite, then the rivals. The JSON holds the same facts and never the answers'
text, which stays in `round.json`.

## Development

```
pip install -e .[dev]
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
