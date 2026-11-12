"""AR11: what the answers claim about a product, each claim traced to its passage.

The table below is SYNTHETIC, in the shape the 12/11/2026 notes describe (the 'without
NVIDIA' answer wrote 'Check build' in its CPU-only column for Modelado); the answers of
that day were not kept verbatim.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from conftest import FakePost

from askround.claims import product_claims
from askround.cli import main
from askround.extract import Claim, verify_claims
from askround.providers import Answer
from askround.round import Result, Round, summary

NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=timezone.utc)

TABLE = """| App | NVIDIA GPU required | CPU only | Verdict |
|---|---|---|---|
| Modelado | No | Check build | **Best fit** |
| Meshroom | Yes | No | Not ideal |
"""

READ = [
    {
        "product": "Modelado",
        "attribute": "NVIDIA GPU required",
        "value": "No",
        "quote": "| Modelado | No | Check build |",
    },
    {
        "product": "Modelado",
        "attribute": "CPU only",
        "value": "Check build",
        "quote": "Modelado | No | Check build",
    },
    {"product": "Meshroom", "attribute": "CPU only", "value": "No", "quote": "Meshroom | Yes | No"},
    {"product": "Modelado", "attribute": "Price", "value": "$20", "quote": "costs $20"},
]


def _answer(provider, text, items):
    answer = Answer(provider, "m", text, {})
    answer.recommendations = []
    answer.claims = verify_claims(text, items)
    return answer


def test_verify_claims_checks_each_quote():
    claims = verify_claims(TABLE, READ)
    assert claims[1] == Claim("Modelado", "CPU only", "Check build", READ[1]["quote"], True)
    assert claims[3].verified is False  # "costs $20" is not in the answer
    assert verify_claims(TABLE, [{"product": "Modelado", "attribute": "", "value": "x"}]) == []


def test_the_products_claims_are_aggregated():
    round_ = Round(
        "q",
        NOW,
        [
            Result("openai", "m", 1, answer=_answer("openai", TABLE, READ)),
            Result("openai", "m", 2, answer=_answer("openai", TABLE, READ[:2])),
            Result("gemini", "m", 1, answer=_answer("gemini", TABLE, [READ[1]])),
        ],
        runs=2,
    )
    found = product_claims(round_, ["Modelado"])
    by = {(c.attribute, c.value): c for c in found}
    cpu = by[("CPU only", "Check build")]
    assert cpu.answers == 3
    assert cpu.providers == {"openai": 2, "gemini": 1}
    assert cpu.quote == READ[1]["quote"]
    assert by[("NVIDIA GPU required", "No")].answers == 2
    price = by[("Price", "$20")]
    assert price.answers == 0
    assert price.unverified == 1
    assert ("CPU only", "No") not in by  # Meshroom's claim, not Modelado's
    data = summary(round_, [["Modelado"]])
    assert data["products"][0]["claims"][0]["attribute"] == "CPU only"
    assert data["results"][0]["claims"][0]["product"] == "Modelado"


class Routed(FakePost):
    def __call__(self, url, headers, body, timeout):
        if body and "text" in body and "format" in body["text"]:
            self.calls.append((url, headers, body))
            reading = {
                "recommendations": [{"name": "Modelado", "quote": "OpenAI says Modelado"}],
                "claims": [
                    {
                        "product": "Modelado",
                        "attribute": "Recommended by",
                        "value": "OpenAI",
                        "quote": "OpenAI says Modelado",
                    }
                ],
            }
            text = json.dumps(reading)
            return {
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]
            }
        return super().__call__(url, headers, body, timeout)


def test_cli_lists_the_claims(all_keys, tmp_path, capsys):
    argv = ["ask", "q", "--provider", "openai", "--runs", "1", "--extract", "openai"]
    code = main([*argv, "--product", "Modelado", "--out", str(tmp_path)], post=Routed())
    out = capsys.readouterr().out
    assert code == 0
    assert "Modelado: what the answers claim" in out
    assert "  Recommended by: OpenAI   (openai 1)" in out
    assert '"OpenAI says Modelado"' in out
