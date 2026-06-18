"""Connection test: ISP Dados RJ (Open Data RJ CKAN plus ISP files).

Auxiliary source for official public-safety history in RJ. Validated in
docs/validacao-fontes-secundarias.md (2026-06-12). No authentication.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

CKAN_PACKAGE_SHOW = "https://dadosabertos.rj.gov.br/api/3/action/package_show"
SECURITY_STATISTICS_PACKAGE_ID = "isp-estatisticas-de-seguranca-publica"
TERRITORIAL_DIVISION_PACKAGE_ID = "isp-divisao-territorial"

# Direct file validated with HTTP 200 during source assessment.
MONTHLY_EVOLUTION_CSV = (
    "https://www.ispdados.rj.gov.br/Arquivos/BaseDPEvolucaoMensalCisp.csv"
)


@pytest.mark.parametrize(
    "package_id",
    [SECURITY_STATISTICS_PACKAGE_ID, TERRITORIAL_DIVISION_PACKAGE_ID],
)
def test_ckan_package_show(http_client: httpx.Client, package_id: str) -> None:
    response = http_client.get(CKAN_PACKAGE_SHOW, params={"id": package_id})

    assert response.status_code == 200, (
        f"CKAN RJ returned status={response.status_code} for {package_id}"
    )
    payload = response.json()
    assert payload.get("success") is True
    resources = payload["result"]["resources"]
    assert isinstance(resources, list) and resources, (
        f"Package {package_id} returned no resources"
    )


def test_monthly_evolution_csv_accessible(http_client: httpx.Client) -> None:
    # Large file: validate response headers without downloading the whole body.
    with http_client.stream("GET", MONTHLY_EVOLUTION_CSV) as response:
        assert response.status_code == 200, (
            f"ISP CSV returned status={response.status_code}"
        )
        content_type = response.headers.get("content-type", "").lower()
        assert any(
            token in content_type for token in ("csv", "text", "octet-stream")
        ), f"Unexpected Content-Type for ISP CSV: {content_type!r}"
