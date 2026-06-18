"""Tests for the IBGE Localidades adapter, without network calls (httpx MockTransport)."""

import httpx
import pytest

from sinal_aberto.adapters.ibge import IbgeError, IbgeLocalidadesClient

_MUNICIPALITIES = [
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


async def test_municipalities_use_long_cache() -> None:
    counter = {"municipalities": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/municipios"):
            counter["municipalities"] += 1
            return httpx.Response(200, json=_MUNICIPALITIES)
        return httpx.Response(404)

    client = _make_client(handler)
    try:
        first = await client.get_municipalities()
        second = await client.get_municipalities()  # Cache: no second HTTP call.
    finally:
        await client.aclose()

    assert first == _MUNICIPALITIES
    assert second == _MUNICIPALITIES
    assert counter["municipalities"] == 1


async def test_non_200_status_raises_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = _make_client(handler)
    try:
        with pytest.raises(IbgeError):
            await client.get_municipalities()
    finally:
        await client.aclose()


async def test_probe_ok_when_catalog_responds() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_MUNICIPALITIES)

    client = _make_client(handler)
    try:
        await client.probe()  # Does not raise.
    finally:
        await client.aclose()


async def test_probe_fails_when_catalog_is_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    client = _make_client(handler)
    try:
        with pytest.raises(IbgeError):
            await client.probe()
    finally:
        await client.aclose()
