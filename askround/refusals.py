"""Refusals: every check that can run before a paid call, with a code and its fix.

A round's mistakes cost money once it is sent: a question that names its product, an
email in a prompt, a provider without a key, a cost above the budget. So every check
that needs no call runs first (law L2), and a refusal lists every problem at once -
each with a code, what was found, and the change that passes it - rather than stopping
at the first and sending the user back and forth. `askround explain <code>` says what a
code means.
"""

from __future__ import annotations

from dataclasses import dataclass

QUESTION_LIMIT = 4000  # characters; a question longer than this is not a question

CODES: dict[str, tuple[str, str]] = {
    "provider.no-key": (
        "No provider that can run here has an API key in the environment.",
        "Set OPENAI_API_KEY, GEMINI_API_KEY (or GOOGLE_API_KEY), ANTHROPIC_API_KEY or PERPLEXITY_API_KEY; `askround doctor` shows which are set.",
    ),
    "provider.unknown": (
        "A provider was named that askround does not know.",
        "Use openai, gemini, anthropic or perplexity.",
    ),
    "question.personal-data": (
        "The question carries personal data: an email address, a phone number, a CPF, an IP address, an API key, or a term on your private list. One round sends it to every provider.",
        "Remove it from the question; ask about the need, not the person.",
    ),
    "question.leading": (
        "The question names the product it tests (its name, an alias, a place or one of its phrases), so the answer measures nothing.",
        "Reword it as a person who does not know the product would ask; or, to ask about the product on purpose, mark it a brand question (--brand, or brand = true in the product file).",
    ),
    "question.too-long": (
        f"The question is longer than {QUESTION_LIMIT} characters.",
        "Ask one question; put context in the product file, not in the prompt.",
    ),
    "question.empty": ("The question is empty.", "Give the question to ask."),
    "cost.over-cap": (
        "The estimate for this run is above the cap set with --max-cost or ASKROUND_MAX_COST.",
        "Ask fewer providers or fewer runs, drop --extract, or raise the cap if you agree to the cost.",
    ),
    "budget.over": (
        "This run's estimate would take the day's or the month's spending past the budget the person set in askround's config file. It is an approval request: the run waits for the person.",
        "The person approves it by running it with --approve, or raises [budget] day / month in the config file (askround budget shows where). An agent asks the person; it cannot approve.",
    ),
    "extract.no-reader": (
        "The extraction pass needs an OpenAI, Gemini or Anthropic key, and none is set (or the one named has none).",
        "Set one of those keys, name one that is set with --extract PROVIDER, or run without --extract.",
    ),
    "extract.needed": (
        "This option reads what the extraction pass finds, and --extract was not given.",
        "Add --extract.",
    ),
    "product.needed": (
        "This option follows a product's links, and no --product (or --product-file) was given.",
        "Name the product with --product NAME,domain.",
    ),
    "product-file.invalid": (
        "The product file cannot be read: it is missing, is not TOML, or lacks a required field.",
        "Fix the file the message names; `askround run --help` and the README show its shape.",
    ),
    "product-file.no-questions": (
        "The product file has no [[question]] to ask.",
        "Add [[question]] entries with a text, or give a --seed to discover.",
    ),
}


@dataclass(frozen=True)
class Problem:
    code: str
    detail: str

    def __str__(self) -> str:
        fix = CODES[self.code][1] if self.code in CODES else ""
        return f"[{self.code}] {self.detail}" + (f"\n      fix: {fix}" if fix else "")


class Checks:
    """Every problem found before a run, kept until all checks have run."""

    def __init__(self) -> None:
        self.problems: list[Problem] = []

    def add(self, code: str, detail: str) -> None:
        if code not in CODES:
            raise KeyError(f"no refusal code {code!r}")
        self.problems.append(Problem(code, detail))

    def __bool__(self) -> bool:
        return bool(self.problems)

    def report(self) -> str:
        head = f"refused before anything was sent: {len(self.problems)} problem(s)"
        return "\n".join([head, *(f"  {p}" for p in self.problems)])


def explain(code: str) -> str:
    if code not in CODES:
        known = "\n".join(f"  {c}" for c in sorted(CODES))
        return f"no code {code!r}; the codes are:\n{known}"
    meaning, fix = CODES[code]
    return f"{code}\n  {meaning}\n  fix: {fix}"
