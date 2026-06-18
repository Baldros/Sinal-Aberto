"""Connection test: Rio de Janeiro GTFS (public ArcGIS/DATA.RIO item).

Auxiliary source for mobility context (bus and BRT routes). Validated in
docs/validacao-fontes-secundarias.md (2026-06-12). No authentication.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

ITEM_ID = "8ffe62ad3b2f42e49814bf941654ea6c"
ITEM_METADATA_URL = f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}"
ITEM_DATA_URL = f"{ITEM_METADATA_URL}/data"


def test_gtfs_item_metadata(http_client: httpx.Client) -> None:
    response = http_client.get(ITEM_METADATA_URL, params={"f": "json"})

    assert response.status_code == 200, (
        f"ArcGIS item returned status={response.status_code}"
    )
    payload = response.json()
    assert "error" not in payload, f"ArcGIS returned error: {payload.get('error')}"
    assert "gtfs" in payload.get("title", "").lower()
    assert payload.get("access") == "public"


def test_gtfs_download_accessible(http_client: httpx.Client) -> None:
    # ZIP with dozens of MB: check only headers, without downloading the body.
    with http_client.stream("GET", ITEM_DATA_URL) as response:
        assert response.status_code == 200, (
            f"GTFS download returned status={response.status_code}"
        )
        content_type = response.headers.get("content-type", "").lower()
        assert "zip" in content_type or "octet-stream" in content_type, (
            f"Unexpected Content-Type for GTFS: {content_type!r}"
        )
