"""Teste de conexao: IBGE Localidades (API REST JSON).

Fonte auxiliar de normalizacao territorial. Validada em
docs/validacao-fontes-secundarias.md (2026-06-12). Sem autenticacao.
"""

import httpx
import pytest


pytestmark = pytest.mark.integration

BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"

# RJ tem 92 municipios oficiais; serve como sanidade do retorno.
RJ_MUNICIPIOS_ESPERADOS = 92


def test_municipios_rj_respondem(http_client: httpx.Client) -> None:
    response = http_client.get(f"{BASE_URL}/estados/RJ/municipios")

    assert response.status_code == 200, (
        f"IBGE Localidades respondeu status={response.status_code}"
    )
    municipios = response.json()
    assert isinstance(municipios, list)
    assert len(municipios) == RJ_MUNICIPIOS_ESPERADOS, (
        f"Esperado {RJ_MUNICIPIOS_ESPERADOS} municipios no RJ, "
        f"obtido {len(municipios)}"
    )


def test_municipio_tem_codigos_oficiais(http_client: httpx.Client) -> None:
    response = http_client.get(f"{BASE_URL}/estados/RJ/municipios")
    assert response.status_code == 200

    municipio = response.json()[0]
    assert isinstance(municipio["id"], int)
    assert isinstance(municipio["nome"], str) and municipio["nome"]

    # A hierarquia territorial completa precisa estar presente para os joins
    # com SINESP/ISP funcionarem.
    microrregiao = municipio["microrregiao"]
    mesorregiao = microrregiao["mesorregiao"]
    uf = mesorregiao["UF"]
    assert uf["sigla"] == "RJ"
    assert uf["nome"] == "Rio de Janeiro"


def test_lista_de_estados_inclui_rj(http_client: httpx.Client) -> None:
    response = http_client.get(f"{BASE_URL}/estados")
    assert response.status_code == 200

    estados = response.json()
    assert isinstance(estados, list)
    siglas = {estado["sigla"] for estado in estados}
    assert "RJ" in siglas
    assert len(estados) == 27, f"Esperado 27 UFs, obtido {len(estados)}"
