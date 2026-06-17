"""Teste de conexao: IBGE Malhas Geograficas (API REST GeoJSON).

Fonte auxiliar de geometrias oficiais. Validada em
docs/validacao-fontes-secundarias.md (2026-06-12). Sem autenticacao.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

BASE_URL = "https://servicodados.ibge.gov.br/api/v3/malhas"

# 33 e o codigo IBGE do estado do Rio de Janeiro.
RJ_CODIGO_IBGE = "33"


def test_malha_rj_geojson_responde(http_client: httpx.Client) -> None:
    response = http_client.get(
        f"{BASE_URL}/estados/{RJ_CODIGO_IBGE}",
        params={"formato": "application/vnd.geo+json", "qualidade": "minima"},
    )

    assert response.status_code == 200, (
        f"IBGE Malhas respondeu status={response.status_code}"
    )
    assert "application/vnd.geo+json" in response.headers.get("content-type", "")

    geojson = response.json()
    assert geojson.get("type") == "FeatureCollection"
    assert isinstance(geojson.get("features"), list)
    assert geojson["features"], "Malha do RJ veio sem features"


def test_malha_aceita_head_apenas_405(http_client: httpx.Client) -> None:
    # Documentado na validacao: a API de malhas nao suporta HEAD e responde
    # 405. Mantemos como regressao para detectar mudanca de comportamento.
    response = http_client.head(
        f"{BASE_URL}/estados/{RJ_CODIGO_IBGE}",
        params={"formato": "application/vnd.geo+json", "qualidade": "minima"},
    )
    assert response.status_code == 405
