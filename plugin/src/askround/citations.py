"""Which pages an answer cites, and which of them are the product's own.

An answer's citations are the sources its provider reported (AR2) plus the links
written in its text, one per page: URLs are normalised so the same page counts once
(tracking parameters such as OpenAI's `utm_source=openai` and fragments dropped, the
host lower-cased, `www.` removed). Gemini reports its sources as
`vertexaisearch.cloud.google.com/grounding-api-redirect/...` links titled with the
domain; askround reads the domain from the title rather than following each redirect,
so a Gemini citation is known by its site, not its page.

A product's places are the names given for it that contain a dot: a domain
(`modelado.app`, which covers its subdomains) or a URL prefix
(`github.com/alegauss/modelado`). A cited page on one of them is the product's, and is
classified by kind - repository (GitHub, GitLab, Hugging Face, ...), store (Microsoft
Store, Google Play, App Store, ...), docs (a `docs.` host or a `/docs` path) or site.
Every other page is third-party, counted by domain, and attributed to a rival when the
rival's name is in its address or title.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from askround import mention

REDIRECT_HOSTS = ("vertexaisearch.cloud.google.com",)
_TRACKING = re.compile(r"^(utm_\w+|ref|ref_src|fbclid|gclid)$", re.IGNORECASE)
_LINK = re.compile(r"https?://[^\s)\]>\"'`]+")

REPOSITORY_HOSTS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "huggingface.co",
    "sourceforge.net",
)
STORE_HOSTS = (
    "apps.microsoft.com",
    "microsoft.com/store",
    "microsoft.com/p/",
    "play.google.com",
    "apps.apple.com",
    "store.steampowered.com",
    "itch.io",
)


@dataclass(frozen=True)
class Cited:
    url: str  # normalised; for a redirect, "https://<domain>/" read from its title
    host: str
    title: str = ""
    redirect: bool = False


def _host(netloc: str) -> str:
    host = netloc.lower().split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def normalise(url: str, title: str = "") -> Cited | None:
    parts = urlsplit(url.strip().rstrip(".,;"))
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    host = _host(parts.netloc)
    if host in REDIRECT_HOSTS:
        domain = _host(title.strip()) if "." in title else ""
        if not domain:
            return None
        return Cited(f"https://{domain}/", domain, title, redirect=True)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING.match(k)])
    path = parts.path.rstrip("/") or "/"
    return Cited(urlunsplit(("https", host, path, query, "")), host, title)


def cited(answer) -> list[Cited]:
    """The answer's pages: its reported sources, then the links in its text."""
    pages: dict[str, Cited] = {}
    for source in answer.sources:
        page = normalise(source.url, source.title)
        if page:
            pages.setdefault(page.url, page)
    for link in _LINK.findall(answer.text):
        page = normalise(link)
        if page:
            pages.setdefault(page.url, page)
    return list(pages.values())


def places(names: list[str]) -> list[str]:
    """The product's own places among its names: "modelado.app", "github.com/x/y"."""
    return [
        n.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").rstrip("/")
        for n in names
        if "." in n
    ]


def _address(page: Cited) -> str:
    rest = urlsplit(page.url).path
    return f"{page.host}{'' if rest == '/' else rest}"


def owns(place: str, page: Cited) -> bool:
    if "/" not in place:
        return page.host == place or page.host.endswith("." + place)
    return (_address(page) + "/").lower().startswith(place + "/") or _address(page).lower() == place


def kind(page: Cited) -> str:
    address = _address(page).lower()
    if any(address.startswith(h) or page.host == h for h in REPOSITORY_HOSTS):
        return "repository"
    if any(address.startswith(h) for h in STORE_HOSTS):
        return "store"
    if page.host.startswith("docs.") or "/docs" in address:
        return "docs"
    return "site"


@dataclass
class ProductCitations:
    """How one provider's answers cited one product's pages."""

    provider: str
    answers: int = 0
    citing: int = 0  # answers that cited at least one of the product's pages
    kinds: dict[str, int] = field(default_factory=dict)  # kind -> answers citing it
    pages: dict[str, int] = field(default_factory=dict)  # url -> answers citing it


def product_citations(round_, names: list[str]) -> list[ProductCitations]:
    own = places(names)
    table: dict[str, ProductCitations] = {}
    for r in round_.results:
        row = table.setdefault(r.provider, ProductCitations(r.provider))
        if r.answer is None:
            continue
        row.answers += 1
        mine = [p for p in cited(r.answer) if any(owns(place, p) for place in own)]
        if mine:
            row.citing += 1
        for k in {kind(p) for p in mine}:
            row.kinds[k] = row.kinds.get(k, 0) + 1
        for page in {p.url for p in mine}:
            row.pages[page] = row.pages.get(page, 0) + 1
    return list(table.values())


def third_party(round_, products: list[list[str]], rival_names: list[str]) -> dict:
    """Pages that are no product's own: answers citing each domain, and each rival's."""
    own = [place for names in products for place in places(names)]
    domains: dict[str, int] = {}
    by_rival: dict[str, int] = {}
    for r in round_.results:
        if r.answer is None:
            continue
        pages = [p for p in cited(r.answer) if not any(owns(place, p) for place in own)]
        for host in {p.host for p in pages}:
            domains[host] = domains.get(host, 0) + 1
        for rival in rival_names:
            needle = mention.core(rival).lower()
            squashed = needle.replace(" ", "")
            if any(
                squashed in _address(p).lower().replace("-", "") or needle in p.title.lower()
                for p in pages
            ):
                by_rival[rival] = by_rival.get(rival, 0) + 1
    ranked = dict(sorted(domains.items(), key=lambda kv: (-kv[1], kv[0])))
    return {"domains": ranked, "rivals": by_rival}
