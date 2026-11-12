"""The one network call askround makes: a JSON POST, or a GET when there is no body.

Every provider goes through `post_json`, so a test replaces this one function (or
passes its own `post` to a provider) and never touches the network. The GET form is
what `askround doctor` uses for the free model lookups that check a key.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

PostJson = Callable[[str, dict[str, str], dict[str, Any] | None, float], dict[str, Any]]


class HttpError(Exception):
    """A non-2xx answer, with the status and the body the provider sent."""

    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


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
        raise HttpError(error.code, error.read().decode("utf-8", "replace")) from None
