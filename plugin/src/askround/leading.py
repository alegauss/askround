"""Leading questions: a question that names the product it tests measures nothing.

On 12/11/2026 the questions were kept neutral by hand: no product name, no domain, no
wording from the product's own page. A question that carries any of them steers the
assistant to the product, and its answer says nothing about whether people find it.

So before a round (law L2: a bad round is refused before it is paid for), each question
is checked against what identifies the product: its name and aliases (whole words), its
places and their hosts (a host shared by many products, such as github.com, does not
count), and the distinctive phrases its product file lists. A question that contains one
is refused - unless it is marked as a brand question (`brand = true` in the product
file, or `--brand`), which asks about the product on purpose and is reported apart.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from askround import mention

SHARED_HOSTS = frozenset(
    {
        "github.com",
        "gitlab.com",
        "bitbucket.org",
        "huggingface.co",
        "apps.microsoft.com",
        "microsoft.com",
        "play.google.com",
        "apps.apple.com",
        "pypi.org",
        "npmjs.com",
        "www.npmjs.com",
        "sourceforge.net",
        "itch.io",
        "store.steampowered.com",
    }
)


def terms(names: list[str], phrases: list[str] | None = None) -> list[str]:
    """What identifies the product: names, places, their own hosts and its phrases."""
    found: list[str] = []
    for name in [*names, *(phrases or [])]:
        name = name.strip()
        if not name:
            continue
        found.append(name)
        if "." in name:
            host = urlsplit(name if "//" in name else f"https://{name}").netloc.lower()
            host = host.removeprefix("www.")
            if host and host not in SHARED_HOSTS and host != name.lower():
                found.append(host)
    return list(dict.fromkeys(found))


def leads(question: str, names: list[str], phrases: list[str] | None = None) -> list[str]:
    """The identifying terms a question contains; empty when it is neutral."""
    hits = []
    for term in terms(names, phrases):
        if mention.pattern([term]).search(question):
            hits.append(term)
    return hits


def refusal(question: str, hits: list[str]) -> str:
    return (
        f"the question names the product it tests ({', '.join(hits)}), so its answer would "
        f"measure nothing: {question!r}. Reword it, or mark it as a brand question "
        "(--brand, or brand = true in the product file) to ask about the product on purpose"
    )
