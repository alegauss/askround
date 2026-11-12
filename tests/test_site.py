"""AR40: the round the site shows is askround's own reading of a recorded live round.

`site/src/round.json` is what `askround ask` reports on the responses recorded live on
2026-11-12 (`tests/fixtures/*-without-nvidia.json`, one answer per provider), plus the
order in which the extraction pass read the OpenAI answer's recommendations that day.
This test asks the round again on the recordings and fails when the page's file says
anything else, so the site cannot drift into a mock. `python tests/test_site.py` writes
the file again after a change to the reading.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SITE_ROUND = HERE.parent / "site" / "src" / "round.json"


def recorded_round() -> dict:
    from test_tokens import READING, Recorded

    from askround import mcp

    out = tempfile.mkdtemp()
    reply = mcp.call(
        "askround_ask",
        {
            "question": READING["question"],
            "providers": ["openai", "gemini"],
            "runs": 1,
            "products": ["Modelado,alegauss.github.io/modelado"],
            "detail": True,
            "fresh": True,
        },
        out,
        Recorded(),
    )
    report = json.loads(reply["content"][0]["text"])["report"]
    (product,) = report["products"]
    return {
        "question": report["question"],
        "asked_on": READING["asked_at"][:10],
        "product": product["product"],
        "answers": [
            {
                "provider": row["provider"],
                "model": row["model"],
                "named": bool(row["named"]),
                "position": row["positions"][0],
            }
            for row in product["frequency"]
        ],
        "cost": round(report["cost"]["total"], 2),
        "read_by": READING["extracted_by"],
        "openai_recommends": [r["name"] for r in READING["recommendations"]],
        # Gemini's answer was not read by the extraction pass that day: the products it
        # names are its own bold headings, in its order
        "gemini_names": re.findall(r"^\*\s+\*\*(.+?)\*\*", gemini_text(), re.M),
    }


def gemini_text() -> str:
    from test_tokens import GEMINI

    return "".join(part.get("text", "") for part in GEMINI["candidates"][0]["content"]["parts"])


def test_the_site_shows_the_recorded_round(all_keys):
    assert json.loads(SITE_ROUND.read_text(encoding="utf-8")) == recorded_round()


if __name__ == "__main__":
    sys.path[:0] = [str(HERE), str(HERE.parent / "plugin" / "src")]
    for name in [n for n in os.environ if n.startswith("ASKROUND_")]:
        del os.environ[name]
    os.environ.update(OPENAI_API_KEY="recorded", GEMINI_API_KEY="recorded")
    os.environ["ASKROUND_CONFIG"] = str(Path(tempfile.mkdtemp()) / "config.toml")
    SITE_ROUND.write_text(json.dumps(recorded_round(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {SITE_ROUND}")
