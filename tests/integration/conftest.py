"""Shared fixtures for auxiliary-source integration tests.

Each source has its own test file to isolate failures, but they all reuse the
same HTTP client configured here.
"""

import httpx
import pytest


# Public agencies can respond slowly; reads get a larger budget while connects
# stay short so unavailable hosts fail quickly.
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=15.0)
USER_AGENT = "SinalAberto-IntegrationTests/1.0 (+https://github.com/Sinal-Aberto)"


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    with httpx.Client(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        yield client
