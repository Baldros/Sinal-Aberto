"""Async adapter for COR.Rio (Centro de Operacoes e Resiliencia do Rio).

Official bulletins for the city of Rio de Janeiro, published as a WordPress REST
feed. Live source with a short cache (critical/live nature, no job, no DB). COR.Rio
sits behind a WAF (server "hcdn") that returns 403 to non browser-like clients, so
browser headers are mandatory and baked in here. Contract validated in
tests/integration/test_cor_rio.py.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

# The WAF needs more than a User-Agent: Accept and Accept-Language are required too.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}

_POSTS_PATH = "/wp-json/wp/v2/posts"
_DEFAULT_CACHE_TTL_SECONDS = 120.0


class CorRioError(RuntimeError):
    """Failure querying the COR.Rio feed."""


class CorRioClient:
    def __init__(
        self,
        *,
        base_url: str = "https://cor.rio",
        timeout: float = 20.0,
        cache_ttl: float = _DEFAULT_CACHE_TTL_SECONDS,
        per_page: int = 15,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._cache_ttl = cache_ttl
        self._per_page = per_page
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=BROWSER_HEADERS,
            transport=transport,
        )
        self._posts: list[dict[str, Any]] | None = None
        self._posts_at = 0.0

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_recent_posts(self) -> list[dict[str, Any]]:
        """Most recent bulletins, with a short cache to absorb bursts."""
        now = time.monotonic()
        if self._posts is not None and now < self._posts_at + self._cache_ttl:
            return self._posts
        response = await self._client.get(_POSTS_PATH, params={"per_page": self._per_page})
        if response.status_code != 200:
            raise CorRioError(f"{_POSTS_PATH} status={response.status_code}")
        posts = response.json() or []
        if not isinstance(posts, list):
            raise CorRioError("posts endpoint did not return a list")
        self._posts = posts
        self._posts_at = now
        return posts

    async def probe(self) -> None:
        """Health probe: confirms the feed answers behind the WAF."""
        await self.get_recent_posts()
