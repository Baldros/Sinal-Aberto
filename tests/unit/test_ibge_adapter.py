"""Testes do adaptador IBGE Localidades, sem rede (httpx MockTransport)."""

import httpx
import pytest

from sinal_aberto.adapters.ibge import IbgeError, IbgeLocalidadesClient

_MUNICIPIOS = [
    {
        "id": 3304557,
        "nome": "Rio de Janeiro",
        "microrregiao": {"mesorregiao": {"UF": {"sigla": "RJ"}}},
    }
]


def _make_client(handler) -> IbgeLocalidadesClient:
    return IbgeLocalidadesClient(
        base_url="http://ibge.test/localidades",
        transport=httpx.MockTransport(handler),
    )


async def test_municipios_usa_cache_longo() -> None:
    counter = {"municipios": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/municipios"):
            counter["municipios"] += 1
            return httpx.Response(200, json=_MUNICIPIOS)
        return httpx.Response(404)

    client = _make_client(handler)
    try:
        first = await client.get_municipios()
        second = await client.get_municipios()  # cache: sem nova chamada HTTP
    finally:
        await client.aclose()

    assert first == _MUNICIPIOS
    assert second == _MUNICIPIOS
    assert counter["municipios"] == 1


async def test_status_nao_200_levanta_erro() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = _make_client(handler)
    try:
        with pytest.raises(IbgeError):
            await client.get_municipios()
    finally:
        await client.aclose()


async def test_probe_ok_quando_catalogo_responde() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_MUNICIPIOS)

    client = _make_client(handler)
    try:
        await client.probe()  # nao levanta
    finally:
        await client.aclose()


async def test_probe_falha_quando_catalogo_vazio() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    client = _make_client(handler)
    try:
        with pytest.raises(IbgeError):
            await client.probe()
    finally:
        await client.aclose()
