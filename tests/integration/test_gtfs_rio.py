"""Teste de conexao: GTFS do Rio de Janeiro (item publico ArcGIS/DATA.RIO).

Fonte auxiliar de mobilidade (linhas de onibus e BRT). Validada em
docs/validacao-fontes-secundarias.md (2026-06-12). Sem autenticacao.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

ITEM_ID = "8ffe62ad3b2f42e49814bf941654ea6c"
ITEM_METADATA_URL = f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}"
ITEM_DATA_URL = f"{ITEM_METADATA_URL}/data"


def test_metadados_do_item_gtfs(http_client: httpx.Client) -> None:
    response = http_client.get(ITEM_METADATA_URL, params={"f": "json"})

    assert response.status_code == 200, (
        f"ArcGIS item respondeu status={response.status_code}"
    )
    payload = response.json()
    assert "error" not in payload, f"ArcGIS retornou erro: {payload.get('error')}"
    assert "gtfs" in payload.get("title", "").lower()
    assert payload.get("access") == "public"


def test_download_gtfs_acessivel(http_client: httpx.Client) -> None:
    # ZIP com dezenas de MB: checamos somente os headers, sem baixar o corpo.
    with http_client.stream("GET", ITEM_DATA_URL) as response:
        assert response.status_code == 200, (
            f"Download do GTFS respondeu status={response.status_code}"
        )
        content_type = response.headers.get("content-type", "").lower()
        assert "zip" in content_type or "octet-stream" in content_type, (
            f"Content-Type inesperado para o GTFS: {content_type!r}"
        )
