"""Write src/self-round.json from a run of askround's own prompt set (AR43).

    askround run examples/askround.toml --runs 1 --extract --json > set.json
    python site/scripts/self-round.py set.json

The site shows the latest round of examples/askround.toml as askround reported it,
including every answer that does not name askround: the numbers are copied from the set's
JSON, never typed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "self-round.json"


def reduce(found: dict) -> dict:
    questions, cost = [], 0.0
    for question in found["questions"]:
        report = question["report"]
        (product,) = report["products"]
        cost += report["cost"]["total"] or 0
        questions.append(
            {
                "text": question["text"],
                "purpose": question["purpose"],
                "answers": [
                    {
                        "provider": row["provider"],
                        "model": row["model"],
                        "runs": row["runs"],
                        "named": row["named"],
                        "best": min((p for p in row["positions"] if p), default=None),
                    }
                    for row in product["frequency"]
                ],
                "rivals": [rival["name"] for rival in report["rivals"]["top"][:5]],
            }
        )
    return {
        "product": found["product"],
        "asked_on": found["asked_at"][:10],
        "cost": round(cost, 2),
        "questions": questions,
    }


if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    OUT.write_text(json.dumps(reduce(data), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
