"""Links an answer attributes to a product, followed to see where they really go.

On 12/11/2026 two answers illustrated Modelado with Microsoft Store pages of other apps.
A reader who clicks such a link installs a rival, and the product's owner never knows.

A link is attributed to the product when it sits in the same table row, list item or
paragraph as the product's name: a Markdown link, an image, or a bare address. Each is
fetched once (the first 64 KB, redirects followed, no cookies) and judged:

- ok: the page it lands on is one of the product's places (`--product NAME,domain`),
  or its title names the product;
- broken: it answers with an error status, or cannot be reached;
- elsewhere: it lands on a page that is neither - another product's, most likely.

Fetching third-party pages is a network call the user did not ask for by asking a
question, so it runs only with `--check-links`.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from askround import citations, mention

# every Markdown target, nested or not: the image and the link of "[![alt](img)](page)"
_MD_LINK = re.compile(r"\]\((https?://[^)\s]+)\)")
_BARE = re.compile(r"(?<![(\[])https?://[^\s)\]>\"'`|]+")
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
READ_LIMIT = 64 * 1024

# (url, timeout) -> (status, final url, the start of the page)
Fetch = Callable[[str, float], tuple[int, str, str]]


@dataclass(frozen=True)
class LinkCheck:
    provider: str
    run: int
    url: str
    status: int  # 0 when the page could not be reached
    final_url: str
    title: str
    verdict: str  # ok, broken or elsewhere


def fetch(url: str, timeout: float = 20.0) -> tuple[int, str, str]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "askround (link check)", "Accept": "text/html,*/*"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(READ_LIMIT).decode("utf-8", "replace")
            return response.status, response.geturl(), body
    except urllib.error.HTTPError as error:
        return error.code, error.geturl() or url, ""
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError):
        return 0, url, ""


NEAR = 120  # in prose, a link this close to the product's name is the product's


def _is_item(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(("|", "- ", "* ", "+ ")) or bool(re.match(r"\d+[.)] ", stripped))


def blocks(text: str) -> list[tuple[str, bool]]:
    """Table rows and list items one by one (True), other text by paragraph (False)."""
    out: list[tuple[str, bool]] = []
    for paragraph in re.split(r"\n\s*\n", text):
        lines = paragraph.splitlines()
        if any(_is_item(line) for line in lines):
            out.extend((line, True) for line in lines)
        else:
            out.append((paragraph, False))
    return out


def _links(block: str) -> list[tuple[int, str]]:
    """Every link in a block with where it starts: Markdown links and images, then bare."""
    found = [(m.start(), m.group(1)) for m in _MD_LINK.finditer(block)]
    blanked = _MD_LINK.sub(lambda m: " " * len(m.group(0)), block)
    found += [(m.start(), m.group(0)) for m in _BARE.finditer(blanked)]
    return sorted(found)


def attributed(text: str, names: list[str]) -> list[str]:
    """The links written beside the product's name, in order, each once: every link of
    a table row or list item that names it, and in prose the links near its name."""
    product = mention.pattern(names)
    found: list[str] = []
    for block, item in blocks(text):
        spots = [m.start() for m in product.finditer(block)]
        if not spots:
            continue
        for start, url in _links(block):
            if not item and min(abs(start - spot) for spot in spots) > NEAR:
                continue
            url = url.rstrip(".,;")
            if url not in found:
                found.append(url)
    return found


def title_of(page: str) -> str:
    match = _TITLE.search(page)
    return " ".join(html.unescape(match.group(1)).split()) if match else ""


def judge(names: list[str], status: int, final_url: str, title: str) -> str:
    if status == 0 or status >= 400:
        return "broken"
    landed = citations.normalise(final_url)
    places = citations.places(names)
    if landed and any(citations.owns(place, landed) for place in places):
        return "ok"
    words = [n for n in names if "." not in n]
    if words and mention.pattern(words).search(title):
        return "ok"
    return "elsewhere"


def check_links(round_, names: list[str], get: Fetch = fetch, parallel: int = 8) -> list[LinkCheck]:
    jobs = [
        (r.provider, r.run, url)
        for r in round_.results
        if r.answer is not None
        for url in attributed(r.answer.text, names)
    ]
    cache: dict[str, tuple[int, str, str]] = {}

    def one(url: str) -> tuple[int, str, str]:
        status, final, page = get(url, 20.0)
        return status, final, title_of(page)

    unique = list(dict.fromkeys(url for _, _, url in jobs))
    with ThreadPoolExecutor(max_workers=max(1, min(len(unique), parallel))) as pool:
        for url, result in zip(unique, pool.map(one, unique), strict=True):
            cache[url] = result
    checks = []
    for provider, run, url in jobs:
        status, final, title = cache[url]
        checks.append(
            LinkCheck(provider, run, url, status, final, title, judge(names, status, final, title))
        )
    return checks
