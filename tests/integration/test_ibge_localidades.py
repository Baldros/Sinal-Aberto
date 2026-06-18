"""Connection test: IBGE Localidades (REST JSON API).

Auxiliary source for territorial normalization. Validated in
docs/validacao-fontes-secundarias.md (2026-06-12). No authentication.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"

# RJ has 92 official municipalities; this is a sanity check for the response.
EXPECTED_RJ_MUNICIPALITIES = 92


def test_rj_municipalities_respond(http_client: httpx.Client) -> None:
    response = http_client.get(f"{BASE_URL}/estados/RJ/municipios")

    assert response.status_code == 200, (
        f"IBGE Localidades returned status={response.status_code}"
    )
    municipalities = response.json()
    assert isinstance(municipalities, list)
    assert len(municipalities) == EXPECTED_RJ_MUNICIPALITIES, (
        f"Expected {EXPECTED_RJ_MUNICIPALITIES} municipalities in RJ, "
        f"got {len(municipalities)}"
    )


def test_municipality_has_official_codes(http_client: httpx.Client) -> None:
    response = http_client.get(f"{BASE_URL}/estados/RJ/municipios")
    assert response.status_code == 200

    municipality = response.json()[0]
    assert isinstance(municipality["id"], int)
    assert isinstance(municipality["nome"], str) and municipality["nome"]

    # The full territorial hierarchy must be present for SINESP/ISP joins.
    microrregiao = municipality["microrregiao"]
    mesorregiao = microrregiao["mesorregiao"]
    uf = mesorregiao["UF"]
    assert uf["sigla"] == "RJ"
    assert uf["nome"] == "Rio de Janeiro"


def test_state_list_includes_rj(http_client: httpx.Client) -> None:
    response = http_client.get(f"{BASE_URL}/estados")
    assert response.status_code == 200

    states = response.json()
    assert isinstance(states, list)
    abbreviations = {state["sigla"] for state in states}
    assert "RJ" in abbreviations
    assert len(states) == 27, f"Expected 27 states, got {len(states)}"
