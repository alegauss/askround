"""AR29: each adapter against its real API, with the smallest call - only when asked.

    ASKROUND_LIVE=1 python -m pytest -m live

Each provider with a key in the environment makes its free check call (`doctor`) and
one short answer with search off; a provider without a key is skipped, so the run says
which adapters were really exercised. The rest of the suite never touches the network.
"""

from __future__ import annotations

import os

import pytest

from askround.providers import all_providers

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("ASKROUND_LIVE") != "1",
        reason="live: set ASKROUND_LIVE=1 to call the real APIs",
    ),
]


@pytest.fixture(autouse=True)
def network(allow_network):
    """Live tests are the only ones that may reach the network."""


@pytest.mark.parametrize("provider", all_providers(), ids=lambda p: p.name)
def test_adapter_against_its_api(provider):
    if not provider.configured():
        pytest.skip(f"{provider.name}: no key in the environment")
    provider.check()
    answer = provider.ask("Reply with the single word OK.", search=False)
    assert answer.text
    assert answer.served_model
