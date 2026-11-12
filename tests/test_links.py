"""AR14: links an answer gives for a product, followed to see where they land.

The answer below is SYNTHETIC, in the shape the 12/11/2026 notes describe: Modelado
illustrated with a Microsoft Store page of another app. The Store ids are made up.
"""

from __future__ import annotations

from datetime import datetime, timezone

from conftest import FakePost

from askround.cli import main
from askround.links import attributed, check_links, judge, title_of
from askround.providers import Answer
from askround.report import build, find_round, load_round, markdown
from askround.round import Result, Round

NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=timezone.utc)
PRODUCT = ["Modelado", "alegauss.github.io/modelado", "apps.microsoft.com/detail/9own"]

ROW = (
    "| Modelado | [![Modelado](https://store-images.example/rival.png)]"
    "(https://apps.microsoft.com/detail/9rival) |"
)
ANSWER = f"""| App | Get it |
|---|---|
{ROW}
| Meshroom | [site](https://meshroom.example/) |

**Modelado** runs on the CPU ([site](https://alegauss.github.io/modelado/)). For other
needs, a much longer paragraph goes on about photogrammetry, cameras, lighting and many
other things before it finally names [Meshroom](https://meshroom.example/download).
"""

PAGES = {
    "https://apps.microsoft.com/detail/9rival": (
        200,
        "https://apps.microsoft.com/detail/9rival",
        "<title>Image to 3d model - Free download | Microsoft Store</title>",
    ),
    "https://store-images.example/rival.png": (200, "https://store-images.example/rival.png", ""),
    "https://alegauss.github.io/modelado/": (
        200,
        "https://alegauss.github.io/modelado/",
        "<title>Modelado</title>",
    ),
    "https://apps.microsoft.com/detail/9own": (
        200,
        "https://apps.microsoft.com/detail/9own",
        "<title>Modelado - Microsoft Store</title>",
    ),
}


def fake_fetch(url, timeout):
    return PAGES.get(url, (404, url, ""))


def test_attributed_takes_the_row_and_the_nearby_prose():
    # in reading order: the image, then the Store page it links to, then the prose link
    assert attributed(ANSWER, ["Modelado"]) == [
        "https://store-images.example/rival.png",
        "https://apps.microsoft.com/detail/9rival",
        "https://alegauss.github.io/modelado/",
    ]
    # Meshroom's links, in its own row and far down the paragraph, are not Modelado's


def test_judge():
    assert judge(PRODUCT, 200, "https://alegauss.github.io/modelado/x", "") == "ok"
    assert judge(PRODUCT, 200, "https://x.example/", "Modelado - Microsoft Store") == "ok"
    assert judge(PRODUCT, 200, "https://apps.microsoft.com/detail/9rival", "Image to 3d model") == (
        "elsewhere"
    )
    assert judge(PRODUCT, 404, "https://x.example/", "") == "broken"
    assert judge(PRODUCT, 0, "https://x.example/", "") == "broken"


def test_title_of():
    assert title_of("<html><TITLE> A &amp; B\n</TITLE>") == "A & B"
    assert title_of("no title") == ""


def test_the_rivals_store_page_is_flagged_and_the_real_pages_pass():
    answer = Answer("openai", "m", ANSWER, {})
    round_ = Round("q", NOW, [Result("openai", "m", 1, answer=answer)], runs=1)
    checks = {c.url: c for c in check_links(round_, PRODUCT, get=fake_fetch)}
    assert checks["https://apps.microsoft.com/detail/9rival"].verdict == "elsewhere"
    assert checks["https://alegauss.github.io/modelado/"].verdict == "ok"
    # an image with no title on a host that is not the product's
    assert checks["https://store-images.example/rival.png"].verdict == "elsewhere"


class LinkingPost(FakePost):
    def __call__(self, url, headers, body, timeout):
        if "api.openai.com/v1/responses" in url:
            message = {"type": "output_text", "text": ANSWER}
            return {"output": [{"type": "message", "content": [message]}]}
        return super().__call__(url, headers, body, timeout)


def test_cli_check_links_and_report(all_keys, tmp_path, capsys):
    argv = ["ask", "q", "--provider", "openai", "--runs", "1", "--check-links"]
    argv += ["--product", ",".join(PRODUCT), "--out", str(tmp_path)]
    code = main(argv, post=LinkingPost(), fetch=fake_fetch)
    out = capsys.readouterr().out
    assert code == 0
    assert "Modelado: links given for it, 3 followed, 2 not its own" in out
    assert "elsewhere: Image to 3d model - Free download | Microsoft Store" in out
    round_, products = load_round(find_round(None, tmp_path))
    report = markdown(build(round_, products))
    assert "Links given for it: 3 followed, 2 not its own." in report
    assert "Image to 3d model - Free download \\| Microsoft Store | elsewhere |" in report


def test_check_links_needs_a_product(all_keys, tmp_path, capsys):
    post = FakePost()
    assert main(["ask", "q", "--check-links", "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
