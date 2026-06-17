"""Teste de conexao: ISP Dados RJ (CKAN do Dados Abertos RJ + arquivos ISP).

Fonte auxiliar de historico oficial de seguranca no RJ. Validada em
docs/validacao-fontes-secundarias.md (2026-06-12). Sem autenticacao.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

CKAN_PACKAGE_SHOW = "https://dadosabertos.rj.gov.br/api/3/action/package_show"
ESTATISTICAS_PACKAGE_ID = "isp-estatisticas-de-seguranca-publica"
DIVISAO_TERRITORIAL_PACKAGE_ID = "isp-divisao-territorial"

# Arquivo direto validado com HTTP 200 no levantamento.
CSV_EVOLUCAO_MENSAL = (
    "https://www.ispdados.rj.gov.br/Arquivos/BaseDPEvolucaoMensalCisp.csv"
)


@pytest.mark.parametrize(
    "package_id",
    [ESTATISTICAS_PACKAGE_ID, DIVISAO_TERRITORIAL_PACKAGE_ID],
)
def test_ckan_package_show(http_client: httpx.Client, package_id: str) -> None:
    response = http_client.get(CKAN_PACKAGE_SHOW, params={"id": package_id})

    assert response.status_code == 200, (
        f"CKAN RJ respondeu status={response.status_code} para {package_id}"
    )
    payload = response.json()
    assert payload.get("success") is True
    resources = payload["result"]["resources"]
    assert isinstance(resources, list) and resources, (
        f"Pacote {package_id} veio sem recursos"
    )


def test_csv_evolucao_mensal_acessivel(http_client: httpx.Client) -> None:
    # Arquivo grande: validamos apenas os headers da resposta sem baixar o
    # corpo inteiro.
    with http_client.stream("GET", CSV_EVOLUCAO_MENSAL) as response:
        assert response.status_code == 200, (
            f"CSV do ISP respondeu status={response.status_code}"
        )
        content_type = response.headers.get("content-type", "").lower()
        assert any(
            token in content_type for token in ("csv", "text", "octet-stream")
        ), f"Content-Type inesperado para o CSV do ISP: {content_type!r}"
