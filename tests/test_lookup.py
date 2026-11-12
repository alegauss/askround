"""AR13: a product an answer recommends is looked up before it is believed."""

from __future__ import annotations

import json

from conftest import FakePost

from askround.cli import main
from askround.lookup import AnthropicWeb, GeminiWeb, OpenAIWeb, Verdict, check, github
from askround.report import build, find_round, load_round, markdown


def _repo(name, stars, owner="someone"):
    return {
        "name": name,
        "full_name": f"{owner}/{name}",
        "html_url": f"https://github.com/{owner}/{name}",
        "stargazers_count": stars,
    }


def _web_answer(status, url, sources):
    verdict = json.dumps({"status": status, "url": url, "evidence": "seen"})
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": verdict,
                        "annotations": [
                            {"type": "url_citation", "url": s, "title": ""} for s in sources
                        ],
                    }
                ],
            }
        ]
    }


class World:
    """GitHub and a web lookup that know Modly, and two app names, made up for this
    test, that nothing knows."""

    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, body))
        if url.startswith("https://api.github.com/search/repositories"):
            if "Modly" in url:
                return {"items": [_repo("modly-docs", 900), _repo("Modly", 4200, "lightningpixel")]}
            if "PhantomForge3D" in url:
                return {"items": [_repo("PhantomForge3D", 1)]}  # a stray repository
            return {"items": []}
        name = body["input"].split('"')[1]
        if name == "Nowhere Shape Studio":
            return _web_answer("not_found", "", [])
        if name == "PhantomForge3D":
            # the model says found, but its page is not among what it searched
            return _web_answer("found", "https://meshforge3d.example/", ["https://other.example/"])
        return _web_answer("ambiguous", "", [])


def test_github_finds_a_popular_repository_of_that_name():
    verdict = github("Modly (open-source desktop app)", World())
    assert verdict == Verdict(
        "Modly (open-source desktop app)",
        "found",
        "https://github.com/lightningpixel/Modly",
        "repository lightningpixel/Modly (4200 stars)",
        "github",
    )


def test_a_stray_repository_is_not_enough():
    assert github("PhantomForge3D", World()) is None


def test_invented_apps_are_flagged_and_modly_is_found(all_keys):
    world = World()
    names = ["Nowhere Shape Studio", "PhantomForge3D", "Modly"]
    verdicts = check(names, "a Windows app, CPU only", post=world, web=OpenAIWeb(post=world))
    by = {v.name: v for v in verdicts}
    assert by["Nowhere Shape Studio"].status == "not_found"
    assert by["PhantomForge3D"].status == "ambiguous"
    assert "not among the pages the search returned" in by["PhantomForge3D"].evidence
    assert by["Modly"].status == "found"
    assert by["Modly"].via == "github"
    # Modly was settled by GitHub, so no paid call was made for it
    assert not any(body and "Modly" in body.get("input", "") for _, body in world.calls)


def test_without_a_web_lookup_an_unsettled_name_stays_unknown():
    verdicts = check(["Nowhere Shape Studio"], post=World(), web=None)
    assert verdicts[0].status == "unknown"


def test_a_github_outage_falls_through_to_the_web(all_keys):
    def down(url, headers, body, timeout):
        if "api.github.com" in url:
            raise OSError("down")
        return _web_answer("found", "https://modly.app/", ["https://modly.app/download"])

    verdicts = check(["Modly"], post=down, web=OpenAIWeb(post=down))
    assert verdicts[0].status == "found"
    assert verdicts[0].via == "web:openai"


def test_each_web_lookup_searches(all_keys):
    for cls in (OpenAIWeb, AnthropicWeb, GeminiWeb):
        _, _, body = cls().request("prompt", "key")
        assert body["tools"]


def test_cli_lookup(all_keys, capsys):
    code = main(["lookup", "Nowhere Shape Studio", "Modly"], post=World())
    out = capsys.readouterr().out
    assert code == 0
    assert "Nowhere Shape Studio: not found" in out
    assert "Modly: found <https://github.com/lightningpixel/Modly>" in out


def test_check_rivals_needs_extract(all_keys, tmp_path, capsys):
    post = FakePost()
    assert main(["ask", "q", "--check-rivals", "--out", str(tmp_path)], post=post) == 2
    assert post.calls == []
    assert "--extract" in capsys.readouterr().err


class RoundWorld(FakePost):
    """A round whose extraction recommends an invented app and Modly."""

    def __init__(self):
        super().__init__()
        self.world = World()

    def __call__(self, url, headers, body, timeout):
        if "api.github.com" in url or (body and "Search the web" in str(body.get("input"))):
            return self.world(url, headers, body, timeout)
        if body and "text" in body and "format" in body["text"]:
            reading = {
                "recommendations": [
                    {"name": "Nowhere Shape Studio", "quote": "x"},
                    {"name": "Modly", "quote": "y"},
                ],
                "claims": [],
            }
            message = {"type": "output_text", "text": json.dumps(reading)}
            return {"output": [{"type": "message", "content": [message]}]}
        if "api.openai.com/v1/responses" in url:
            return {"output": [_message("1. Nowhere Shape Studio\n2. Modly")]}
        return super().__call__(url, headers, body, timeout)


def _message(text):
    return {"type": "message", "content": [{"type": "output_text", "text": text}]}


def test_ask_check_rivals_flags_and_reports(all_keys, tmp_path, capsys):
    argv = ["ask", "q", "--provider", "openai", "--runs", "1", "--extract", "openai"]
    code = main([*argv, "--check-rivals", "--out", str(tmp_path)], post=RoundWorld())
    out = capsys.readouterr().out
    assert code == 0
    assert "Nowhere Shape Studio" in out and "[not found]" in out
    assert "[found]" in out
    round_, products = load_round(find_round(None, tmp_path))
    report = markdown(build(round_, products))
    assert "**Not found anywhere:** Nowhere Shape Studio." in report
    assert "[found](https://github.com/lightningpixel/Modly)" in report
