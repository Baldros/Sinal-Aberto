"""Tests for the COR.Rio adapter, without network calls (httpx MockTransport)."""

import httpx
import pytest

from sinal_aberto.adapters.cor_rio import BROWSER_HEADERS, CorRioClient, CorRioError

_POSTS = [{"id": 1, "title": {"rendered": "Operação policial"}, "date_gmt": "2026-06-17T15:00:00"}]


def _make_client(handler) -> CorRioClient:
    return CorRioClient(base_url="http://cor.test", transport=httpx.MockTransport(handler))


async def test_posts_use_short_cache_and_send_browser_headers() -> None:
    counter = {"posts": 0, "saw_user_agent": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/wp-json/wp/v2/posts"):
            counter["posts"] += 1
            counter["saw_user_agent"] = request.headers.get("User-Agent") == BROWSER_HEADERS["User-Agent"]
            return httpx.Response(200, json=_POSTS)
        return httpx.Response(404)

    client = _make_client(handler)
    try:
        first = await client.get_recent_posts()
        second = await client.get_recent_posts()  # cache: no second HTTP call
    finally:
        await client.aclose()

    assert first == _POSTS and second == _POSTS
    assert counter["posts"] == 1
    assert counter["saw_user_agent"] is True


async def test_non_200_raises_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)  # the WAF without proper headers

    client = _make_client(handler)
    try:
        with pytest.raises(CorRioError):
            await client.get_recent_posts()
    finally:
        await client.aclose()


async def test_probe_ok_when_feed_responds() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_POSTS)

    client = _make_client(handler)
    try:
        await client.probe()  # does not raise
    finally:
        await client.aclose()
