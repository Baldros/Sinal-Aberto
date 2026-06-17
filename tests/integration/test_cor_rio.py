"""Connection test: COR.Rio (WordPress REST + RSS).

Auxiliary source for official context with low evidentiary weight. Validated in
docs/validacao-fontes-secundarias.md (2026-06-12). No authentication.
"""

import xml.etree.ElementTree as ET

import httpx
import pytest


pytestmark = pytest.mark.integration

WP_POSTS_URL = "https://cor.rio/wp-json/wp/v2/posts"
RSS_FEED_URL = "https://cor.rio/feed/"

# COR.Rio sits behind a WAF (server "hcdn") that returns 403 to clients that do
# not look browser-like. Changing only User-Agent is not enough; Accept and
# Accept-Language are also required. A real source client must send these headers.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}


def test_wordpress_rest_posts(http_client: httpx.Client) -> None:
    response = http_client.get(
        WP_POSTS_URL, params={"per_page": 3}, headers=BROWSER_HEADERS
    )

    assert response.status_code == 200, (
        f"WordPress REST returned status={response.status_code}"
    )
    posts = response.json()
    assert isinstance(posts, list) and posts
    assert len(posts) <= 3

    post = posts[0]
    assert isinstance(post.get("id"), int)
    assert post.get("date"), "Post without date"
    assert "rendered" in post.get("title", {})


def test_rss_feed_parseable(http_client: httpx.Client) -> None:
    response = http_client.get(RSS_FEED_URL, headers=BROWSER_HEADERS)

    assert response.status_code == 200, (
        f"COR.Rio RSS returned status={response.status_code}"
    )
    content_type = response.headers.get("content-type", "").lower()
    assert "xml" in content_type or "rss" in content_type, (
        f"Unexpected Content-Type for RSS: {content_type!r}"
    )

    root = ET.fromstring(response.content)
    assert root.tag == "rss"
    channel = root.find("channel")
    assert channel is not None
    assert channel.find("item") is not None, "RSS feed has no items"
