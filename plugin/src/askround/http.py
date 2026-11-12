"""The one network call askround makes: a JSON POST, or a GET when there is no body.

Every provider goes through `post_json`, so a test replaces this one function (or
passes its own `post` to a provider) and never touches the network. The GET form is
what `askround doctor` uses for the free model lookups that check a key.

`with_retries` wraps it: a rate limit, an overloaded or failing server, a timeout or
a dropped connection is retried with exponential backoff (honouring `Retry-After`),
and anything else - a rejected key, a missing model, a malformed request - fails at
once, because asking again would only fail again. The error that finally escapes
carries `attempts`, so a report can say "failed after 3 attempts".
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

PostJson = Callable[[str, dict[str, str], dict[str, Any] | None, float], dict[str, Any]]

# 408 timeout, 409 conflict, 425 too early, 429 rate limit, 5xx server, 529 overloaded
TRANSIENT_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504, 529})
ATTEMPTS = 3
BASE_DELAY = 2.0
MAX_DELAY = 60.0

# replaced in tests, so a retried call never waits
sleep = time.sleep


class HttpError(Exception):
    """A non-2xx answer, with the status and the body the provider sent."""

    def __init__(self, status: int, body: str, retry_after: float | None = None):
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body
        self.retry_after = retry_after


def post_json(
    url: str, headers: dict[str, str], body: dict[str, Any] | None, timeout: float
) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        retry_after = _seconds(error.headers.get("Retry-After") if error.headers else None)
        raise HttpError(error.code, error.read().decode("utf-8", "replace"), retry_after) from None


def _seconds(value: str | None) -> float | None:
    try:
        return max(0.0, float(value)) if value else None
    except ValueError:
        return None  # an HTTP date: fall back to the backoff


def transient(error: BaseException) -> bool:
    if isinstance(error, HttpError):
        return error.status in TRANSIENT_STATUS
    if isinstance(error, urllib.error.URLError):
        return True  # DNS, refused or reset connection, or a timeout inside urllib
    return isinstance(error, TimeoutError | ConnectionError)  # socket.timeout included


def with_retries(
    post: PostJson, attempts: int = ATTEMPTS, base_delay: float = BASE_DELAY
) -> PostJson:
    def call(url, headers, body, timeout):
        for attempt in range(1, attempts + 1):
            try:
                return post(url, headers, body, timeout)
            except Exception as error:
                if attempt == attempts or not transient(error):
                    error.attempts = attempt  # type: ignore[attr-defined]
                    raise
                hinted = getattr(error, "retry_after", None)
                delay = hinted if hinted is not None else base_delay * 2 ** (attempt - 1)
                sleep(min(delay, MAX_DELAY))
        raise AssertionError("unreachable")

    return call
