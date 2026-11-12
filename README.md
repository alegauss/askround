# askround

Ask several AI assistants the same question and keep their answers side by side.

```
pip install -e .
askround ask "What is the best free app to turn a photo into a 3D model on Windows?"
```

Every provider whose API key is in the environment is asked in parallel:
`OPENAI_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and `ANTHROPIC_API_KEY`.
askround reads the keys at call time and never stores them.

Each round is saved under `.askround/rounds/<date>/<time>-<question>/` (change it with
`--out` or `ASKROUND_DIR`): `round.json` holds the question and each provider's answer,
and `<provider>.json` the raw response as the provider sent it.

| Option              | What it does                                        |
| ------------------- | --------------------------------------------------- |
| `--provider NAME`   | ask only this provider (`openai`, `gemini`, `anthropic`), repeatable |
| `--out DIR`         | where the round is saved                            |
| `--json`            | print the round as JSON                             |

The model per provider is overridden with `ASKROUND_OPENAI_MODEL`,
`ASKROUND_GEMINI_MODEL` and `ASKROUND_ANTHROPIC_MODEL`.

## Development

```
pip install -e .[dev]
python -m pytest
python -m ruff check .
python -m ruff format --check .
```
