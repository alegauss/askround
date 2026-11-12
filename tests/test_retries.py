"""AR7: transient failures are retried with backoff; a call that still fails costs
its answer only, and the round reports it."""

from __future__ import annotations

import urllib.error

import pytest
from conftest import OPENAI_RAW, FakePost

from askround.cli import main
from askround.http import HttpError, transient, with_retries
from askround.providers import OpenAI, by_name
from askround.round import run_round, summary


class Flaky:
    """Fails with the given errors in order, then answers."""

    def __init__(self, *errors: BaseException):
        self.errors = list(errors)
        self.calls = 0

    def __call__(self, url, headers, body, timeout):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return OPENAI_RAW


@pytest.mark.parametrize(
    "error",
    [
        HttpError(429, "rate limited"),
        HttpError(500, "boom"),
        HttpError(503, "unavailable"),
        HttpError(529, "overloaded"),
        TimeoutError("timed out"),
        ConnectionResetError("reset"),
        urllib.error.URLError("refused"),
    ],
)
def test_transient(error):
    assert transient(error)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_not_transient(status):
    assert not transient(HttpError(status, "no"))


def test_retried_with_exponential_backoff(no_waiting):
    post = Flaky(HttpError(429, "slow down"), HttpError(503, "busy"))
    assert with_retries(post, attempts=3, base_delay=2.0)("u", {}, {}, 1.0) == OPENAI_RAW
    assert post.calls == 3
    assert no_waiting == [2.0, 4.0]


def test_retry_after_is_honoured_and_capped(no_waiting):
    post = Flaky(HttpError(429, "x", retry_after=7.0), HttpError(429, "x", retry_after=600.0))
    with_retries(post, attempts=3)("u", {}, {}, 1.0)
    assert no_waiting == [7.0, 60.0]


def test_gives_up_after_the_last_attempt_and_says_so(no_waiting):
    post = Flaky(*[HttpError(500, "boom")] * 5)
    with pytest.raises(HttpError) as raised:
        with_retries(post, attempts=3)("u", {}, {}, 1.0)
    assert post.calls == 3
    assert raised.value.attempts == 3


def test_a_rejected_key_is_not_retried(no_waiting):
    post = Flaky(HttpError(401, "bad key"))
    with pytest.raises(HttpError) as raised:
        with_retries(post)("u", {}, {}, 1.0)
    assert post.calls == 1
    assert raised.value.attempts == 1
    assert no_waiting == []


def test_provider_retries_a_rate_limit(all_keys):
    post = Flaky(HttpError(429, "slow down"))
    answer = OpenAI(post=post).ask("q")
    assert post.calls == 2
    assert answer.text == "OpenAI says Modelado."


def test_a_round_with_a_failing_provider_finishes_and_reports_it(all_keys, tmp_path, capsys):
    post = FakePost(fail={"api.anthropic.com": 503})
    argv = ["ask", "q", "--provider", "openai", "--provider", "anthropic", "--runs", "2"]
    code = main([*argv, "--out", str(tmp_path)], post=post)
    out = capsys.readouterr().out
    assert code == 0
    assert out.count("OpenAI says Modelado.") == 2
    assert "failed: 2 of 4 answers" in out
    assert "anthropic run 1: HttpError: HTTP 503: boom" in out
    assert "(after 3 attempts)" in out
    anthropic_calls = [url for url, _, _ in post.calls if "anthropic" in url]
    assert len(anthropic_calls) == 2 * 3


def test_round_json_counts_failures(all_keys):
    post = FakePost(fail={"api.anthropic.com": 404})
    round_ = run_round("q", by_name(["openai", "anthropic"], post=post), runs=1)
    data = summary(round_)
    assert data["answered"] == 1
    assert data["failed"] == 1
    failed = next(r for r in data["results"] if r["provider"] == "anthropic")
    # a 404 is not retried, so no attempt count is added
    assert failed["error"].startswith("HttpError: HTTP 404")
    assert "attempts" not in failed["error"]
