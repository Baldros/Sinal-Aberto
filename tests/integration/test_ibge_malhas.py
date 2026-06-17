"""Connection test: IBGE Malhas Geograficas (REST GeoJSON API).

Auxiliary source for official geometries. Validated in
docs/validacao-fontes-secundarias.md (2026-06-12). No authentication.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

BASE_URL = "https://servicodados.ibge.gov.br/api/v3/malhas"

# 33 is the IBGE code for Rio de Janeiro state.
RJ_IBGE_CODE = "33"


def test_rj_mesh_geojson_responds(http_client: httpx.Client) -> None:
    response = http_client.get(
        f"{BASE_URL}/estados/{RJ_IBGE_CODE}",
        params={"formato": "application/vnd.geo+json", "qualidade": "minima"},
    )

    assert response.status_code == 200, (
        f"IBGE Malhas returned status={response.status_code}"
    )
    assert "application/vnd.geo+json" in response.headers.get("content-type", "")

    geojson = response.json()
    assert geojson.get("type") == "FeatureCollection"
    assert isinstance(geojson.get("features"), list)
    assert geojson["features"], "RJ mesh returned no features"


def test_mesh_accepts_head_only_as_405(http_client: httpx.Client) -> None:
    # Documented in validation: the mesh API does not support HEAD and returns
    # 405. Keep this as a regression check for behavior changes.
    response = http_client.head(
        f"{BASE_URL}/estados/{RJ_IBGE_CODE}",
        params={"formato": "application/vnd.geo+json", "qualidade": "minima"},
    )
    assert response.status_code == 405
