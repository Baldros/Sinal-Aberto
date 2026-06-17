"""Testes do adaptador Fogo Cruzado, sem rede (httpx MockTransport)."""

from datetime import datetime, timezone

import httpx
import pytest

from sinal_aberto.adapters.fogocruzado import (
    FogoCruzadoClient,
    FogoCruzadoError,
    parse_api_datetime,
)


def _login_response(token: str = "tok") -> httpx.Response:
    return httpx.Response(
        201, json={"code": 201, "data": {"accessToken": token, "expiresIn": 3600}}
    )


def _make_client(handler) -> FogoCruzadoClient:
    return FogoCruzadoClient(
        base_url="http://fogocruzado.test",
        email="e@example.com",
        password="secret",
        transport=httpx.MockTransport(handler),
    )


# -- parse_api_datetime ------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-06-17T10:00:00Z", datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)),
        ("2026-06-17T10:00:00-03:00", datetime(2026, 6, 17, 13, 0, tzinfo=timezone.utc)),
    ],
)
def test_parse_api_datetime_iso(value: str, expected: datetime) -> None:
    parsed = parse_api_datetime(value)
    assert parsed is not None
    assert parsed.astimezone(timezone.utc) == expected


def test_parse_api_datetime_naive_assume_utc() -> None:
    parsed = parse_api_datetime("2026-06-17 10:00:00")
    assert parsed == datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", [None, "", "nao-e-data"])
def test_parse_api_datetime_invalido(value) -> None:
    assert parse_api_datetime(value) is None


# -- autenticacao e cache ----------------------------------------------


async def test_token_reaproveitado_entre_requisicoes() -> None:
    counter = {"login": 0, "cities": 0, "occurrences": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/login"):
            counter["login"] += 1
            return _login_response(f"tok{counter['login']}")
        if path.endswith("/cities"):
            counter["cities"] += 1
            return httpx.Response(200, json={"code": 200, "data": [{"id": "c1"}]})
        if path.endswith("/occurrences"):
            counter["occurrences"] += 1
            return httpx.Response(200, json={"code": 200, "data": [], "pageMeta": {}})
        return httpx.Response(404)

    client = _make_client(handler)
    try:
        await client.get_cities()
        await client.get_cities()  # cache: nao deve gerar nova chamada HTTP
        await client.get_occurrences({"page": 1})
    finally:
        await client.aclose()

    assert counter["login"] == 1  # token reaproveitado
    assert counter["cities"] == 1  # segunda consulta veio do cache
    assert counter["occurrences"] == 1


async def test_reautentica_apos_401() -> None:
    state = {"login": 0, "occ": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/login"):
            state["login"] += 1
            return _login_response(f"tok{state['login']}")
        if path.endswith("/occurrences"):
            state["occ"] += 1
            if state["occ"] == 1:
                return httpx.Response(401, json={"code": 401})
            return httpx.Response(
                200,
                json={"code": 200, "data": [{"id": "x"}], "pageMeta": {}},
                headers={"x-last-update": "2026-06-17T10:00:00Z"},
            )
        return httpx.Response(404)

    client = _make_client(handler)
    try:
        data, _meta, last_update = await client.get_occurrences({"page": 1})
    finally:
        await client.aclose()

    assert state["login"] == 2  # relogou apos o 401
    assert state["occ"] == 2  # repetiu a chamada
    assert data == [{"id": "x"}]
    assert last_update == datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)


async def test_login_falho_levanta_erro() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(500, json={"code": 500})
        return httpx.Response(404)

    client = _make_client(handler)
    try:
        with pytest.raises(FogoCruzadoError):
            await client.get_cities()
    finally:
        await client.aclose()


async def test_probe_retorna_last_update() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/login"):
            return _login_response()
        if path.endswith("/occurrences"):
            return httpx.Response(
                200,
                json={"code": 200, "data": [], "pageMeta": {}},
                headers={"x-last-update": "2026-06-17T09:30:00Z"},
            )
        return httpx.Response(404)

    client = _make_client(handler)
    try:
        last_update = await client.probe()
    finally:
        await client.aclose()

    assert last_update == datetime(2026, 6, 17, 9, 30, tzinfo=timezone.utc)
