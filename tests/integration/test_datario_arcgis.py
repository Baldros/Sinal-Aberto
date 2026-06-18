"""Connection test: DATA.RIO (ArcGIS REST / FeatureServer).

Auxiliary source for urban layers in Rio de Janeiro city. Validated in
docs/validacao-fontes-secundarias.md (2026-06-12). Access is dataset-based;
this file tests the neighborhood-boundary layer. No authentication.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

LAYER_URL = (
    "https://pgeo3.rio.rj.gov.br/arcgis/rest/services/"
    "Cartografia/Limites_administrativos/FeatureServer/4"
)


def test_neighborhood_layer_metadata(http_client: httpx.Client) -> None:
    response = http_client.get(LAYER_URL, params={"f": "json"})

    assert response.status_code == 200, (
        f"ArcGIS DATA.RIO returned status={response.status_code}"
    )
    payload = response.json()
    # ArcGIS signals logical errors with HTTP 200 plus an "error" key.
    assert "error" not in payload, f"ArcGIS returned error: {payload.get('error')}"
    assert "bairro" in payload.get("name", "").lower()
    assert payload.get("geometryType") == "esriGeometryPolygon"
    assert isinstance(payload.get("fields"), list) and payload["fields"]


def test_query_returns_neighborhoods(http_client: httpx.Client) -> None:
    response = http_client.get(
        f"{LAYER_URL}/query",
        params={
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "resultRecordCount": 3,
            "f": "json",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "error" not in payload, f"ArcGIS returned error: {payload.get('error')}"
    features = payload.get("features")
    assert isinstance(features, list) and features
    assert len(features) <= 3
    assert "attributes" in features[0]
