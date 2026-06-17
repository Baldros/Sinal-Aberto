"""Teste de conexao: DATA.RIO (ArcGIS REST / FeatureServer).

Fonte auxiliar de camadas urbanas do municipio do Rio. Validada em
docs/validacao-fontes-secundarias.md (2026-06-12). Acesso por dataset; aqui
testamos a camada de Limite de Bairros. Sem autenticacao.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

LAYER_URL = (
    "https://pgeo3.rio.rj.gov.br/arcgis/rest/services/"
    "Cartografia/Limites_administrativos/FeatureServer/4"
)


def test_metadados_da_camada_de_bairros(http_client: httpx.Client) -> None:
    response = http_client.get(LAYER_URL, params={"f": "json"})

    assert response.status_code == 200, (
        f"ArcGIS DATA.RIO respondeu status={response.status_code}"
    )
    payload = response.json()
    # O ArcGIS sinaliza erro com HTTP 200 + chave "error".
    assert "error" not in payload, f"ArcGIS retornou erro: {payload.get('error')}"
    assert "bairro" in payload.get("name", "").lower()
    assert payload.get("geometryType") == "esriGeometryPolygon"
    assert isinstance(payload.get("fields"), list) and payload["fields"]


def test_query_retorna_bairros(http_client: httpx.Client) -> None:
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
    assert "error" not in payload, f"ArcGIS retornou erro: {payload.get('error')}"
    features = payload.get("features")
    assert isinstance(features, list) and features
    assert len(features) <= 3
    assert "attributes" in features[0]
