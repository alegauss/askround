"""AR10: which pages an answer cites, and which of them are the product's own."""

from __future__ import annotations

from datetime import datetime, timezone

from conftest import FakePost

from askround.citations import Cited, cited, kind, normalise, owns, places, product_citations
from askround.cli import main
from askround.providers import Answer, Source
from askround.round import Result, Round, summary

NOW = datetime(2026, 11, 12, 14, 30, 5, tzinfo=timezone.utc)
PRODUCT = [
    "Modelado",
    "modelado.app",
    "github.com/alegauss/modelado",
    "apps.microsoft.com/detail/9n1",
]


def test_normalise_drops_tracking_and_www():
    page = normalise("https://www.Modelado.app/download/?utm_source=openai#top")
    assert page == Cited("https://modelado.app/download", "modelado.app")
    assert normalise("https://x.example/p?id=3&utm_medium=chat").url == "https://x.example/p?id=3"


def test_gemini_redirect_is_known_by_its_title():
    url = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQ"
    assert normalise(url, "modelado.app") == Cited(
        "https://modelado.app/", "modelado.app", "modelado.app", redirect=True
    )
    assert normalise(url, "") is None


def test_cited_merges_sources_and_text_links_once():
    answer = Answer(
        "openai",
        "m",
        "See [the site](https://modelado.app/?utm_source=openai) and https://github.com/alegauss/modelado.",
        {},
        sources=[Source("https://modelado.app/", "Modelado")],
    )
    assert [p.url for p in cited(answer)] == [
        "https://modelado.app/",
        "https://github.com/alegauss/modelado",
    ]


def test_places_and_ownership():
    own = places(PRODUCT)
    assert own == ["modelado.app", "github.com/alegauss/modelado", "apps.microsoft.com/detail/9n1"]
    assert owns("modelado.app", normalise("https://docs.modelado.app/start"))
    assert owns(
        "github.com/alegauss/modelado", normalise("https://github.com/alegauss/modelado/releases")
    )
    assert not owns(
        "github.com/alegauss/modelado", normalise("https://github.com/alegauss/modelador")
    )
    assert not owns("modelado.app", normalise("https://notmodelado.app/"))


def test_kind():
    assert kind(normalise("https://github.com/alegauss/modelado")) == "repository"
    assert kind(normalise("https://apps.microsoft.com/detail/9n1")) == "store"
    assert kind(normalise("https://docs.modelado.app/x")) == "docs"
    assert kind(normalise("https://modelado.app/")) == "site"


def _round():
    a = Answer(
        "openai",
        "m",
        "1. Modelado ([modelado.app](https://modelado.app/?utm_source=openai))",
        {},
        sources=[
            Source("https://github.com/alegauss/modelado", "repo"),
            Source("https://modly.app/", "Modly"),
        ],
    )
    b = Answer("openai", "m", "1. Modly", {}, sources=[Source("https://modly.app/", "Modly")])
    g = Answer(
        "gemini",
        "m",
        "1. Modelado",
        {},
        sources=[
            Source(
                "https://vertexaisearch.cloud.google.com/grounding-api-redirect/X", "modelado.app"
            )
        ],
    )
    results = [
        Result("openai", "m", 1, answer=a),
        Result("openai", "m", 2, answer=b),
        Result("gemini", "m", 1, answer=g),
    ]
    return Round("q", NOW, results, runs=2)


def test_product_citations_per_provider():
    rows = {c.provider: c for c in product_citations(_round(), PRODUCT)}
    assert rows["openai"].answers == 2
    assert rows["openai"].citing == 1
    assert rows["openai"].kinds == {"repository": 1, "site": 1}
    assert rows["openai"].pages == {
        "https://modelado.app/": 1,
        "https://github.com/alegauss/modelado": 1,
    }
    assert rows["gemini"].kinds == {"site": 1}


def test_round_json_carries_citations_and_third_party_pages():
    data = summary(_round(), [PRODUCT])
    product = data["products"][0]
    assert product["places"][0] == "modelado.app"
    assert product["cited"][0]["citing"] == 1
    assert data["third_party"]["domains"] == {"modly.app": 2}


def test_cli_reports_which_pages_were_cited(all_keys, tmp_path, capsys):
    argv = ["ask", "q", "--provider", "openai", "--runs", "1"]
    code = main(
        [*argv, "--product", "Modelado,modelado.app", "--out", str(tmp_path)], post=FakePost()
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Modelado: its pages cited in" in out
    assert "openai      1/1 answers   (site 1)" in out
    assert "1x https://modelado.app/" in out


def test_cli_asks_for_a_domain_when_none_given(all_keys, tmp_path, capsys):
    argv = ["ask", "q", "--provider", "openai", "--runs", "1", "--product", "Modelado"]
    main([*argv, "--out", str(tmp_path)], post=FakePost())
    assert "--product Modelado,example.com" in capsys.readouterr().out
