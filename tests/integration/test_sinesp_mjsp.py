"""Teste de conexao: SINESP/MJSP (CKAN do Ministerio da Justica).

Fonte auxiliar de historico nacional agregado. Validada em
docs/validacao-fontes-secundarias.md (2026-06-12). Sem autenticacao.
"""

from datetime import datetime

import httpx
import pytest


pytestmark = pytest.mark.integration

CKAN_PACKAGE_SHOW = "https://dados.mj.gov.br/api/3/action/package_show"
SINESP_PACKAGE_ID = "sistema-nacional-de-estatisticas-de-seguranca-publica"


@pytest.fixture(scope="module")
def sinesp_package(http_client: httpx.Client) -> dict:
    response = http_client.get(CKAN_PACKAGE_SHOW, params={"id": SINESP_PACKAGE_ID})
    assert response.status_code == 200, (
        f"CKAN MJSP respondeu status={response.status_code}"
    )
    payload = response.json()
    assert payload.get("success") is True
    return payload["result"]


def test_pacote_tem_licenca_e_data_valida(sinesp_package: dict) -> None:
    # Licenca aberta foi um dos criterios de uso da fonte.
    license_id = (sinesp_package.get("license_id") or "").lower()
    license_title = (sinesp_package.get("license_title") or "").lower()
    assert "cc" in license_id or "creative commons" in license_title, (
        f"Licenca inesperada: id={license_id!r} title={license_title!r}"
    )

    # metadata_modified deve ser um timestamp ISO real; parse via stdlib em vez
    # de comparar string crua.
    modified = datetime.fromisoformat(sinesp_package["metadata_modified"])
    assert modified.year >= 2020


def test_pacote_tem_recurso_zip(sinesp_package: dict) -> None:
    resources = sinesp_package["resources"]
    assert isinstance(resources, list) and resources

    zip_resources = [
        resource
        for resource in resources
        if (resource.get("format") or "").upper() == "ZIP"
        or (resource.get("url") or "").lower().endswith(".zip")
    ]
    assert zip_resources, "SINESP nao expoe nenhum recurso ZIP"


def test_recurso_zip_acessivel(
    http_client: httpx.Client,
    sinesp_package: dict,
) -> None:
    # Deriva a URL do ZIP do proprio CKAN (UUIDs mudam) e checa apenas os
    # headers; o arquivo tem dezenas de MB.
    zip_url = next(
        resource["url"]
        for resource in sinesp_package["resources"]
        if (resource.get("format") or "").upper() == "ZIP"
        or (resource.get("url") or "").lower().endswith(".zip")
    )

    with http_client.stream("GET", zip_url) as response:
        assert response.status_code == 200, (
            f"ZIP do SINESP respondeu status={response.status_code}"
        )
        content_type = response.headers.get("content-type", "").lower()
        assert "zip" in content_type or "octet-stream" in content_type, (
            f"Content-Type inesperado para o ZIP do SINESP: {content_type!r}"
        )
