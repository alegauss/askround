# askround

Ask several AI assistants the same question and keep their answers side by side.

```
pip install -e .
askround ask "What is the best free app to turn a photo into a 3D model on Windows?"
```

Every provider whose API key is in the environment is asked in parallel:
`OPENAI_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), `ANTHROPIC_API_KEY` and
`PERPLEXITY_API_KEY`. askround reads the keys at call time and never stores them.

Web search is on, through each provider's own search tool, because that is how
assistants find and recommend products. Each answer is printed with the sources it
cited. `--no-search` asks the same question without search, to compare.

Each round is saved under `.askround/rounds/<date>/<time>-<question>/` (change it with
`--out` or `ASKROUND_DIR`): `round.json` holds the question and each provider's answer,
search queries and sources, and `<provider>.json` the raw response as the provider sent
it.

| Option              | What it does                                        |
| ------------------- | --------------------------------------------------- |
| `--provider NAME`   | ask only this provider (`openai`, `gemini`, `anthropic`, `perplexity`), repeatable |
| `--no-search`       | ask without web search                              |
| `--out DIR`         | where the round is saved                            |
| `--json`            | print the round as JSON                             |

The model per provider is overridden with `ASKROUND_OPENAI_MODEL`,
`ASKROUND_GEMINI_MODEL`, `ASKROUND_ANTHROPIC_MODEL` and `ASKROUND_PERPLEXITY_MODEL`.

## Development

```
pip install -e .[dev]
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
