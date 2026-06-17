"""Adaptador assincrono da API Fogo Cruzado.

Encapsula autenticacao JWT (com cache de token em memoria), consulta de cidades
(com cache curto) e de ocorrencias. As tools MCP nao falam diretamente com a API:
passam por aqui. Contrato dos endpoints validado em
tests/integration/test_fogocruzado_api.py.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

# Margem de seguranca para renovar o token antes de expirar.
_TOKEN_REFRESH_MARGIN_SECONDS = 30.0
_DEFAULT_TOKEN_TTL_SECONDS = 3600.0


def parse_api_datetime(value: str | None) -> datetime | None:
    """Converte um timestamp da API em datetime aware (UTC quando sem tz)."""
    if not value:
        return None
    text = value.strip()
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class FogoCruzadoError(RuntimeError):
    """Falha ao consultar a API Fogo Cruzado."""


class FogoCruzadoClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        password: str,
        timeout: float = 20.0,
        catalog_ttl: float = 300.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._email = email
        self._password = password
        self._catalog_ttl = catalog_ttl
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport
        )
        self._token: str | None = None
        self._token_expiry = 0.0
        self._auth_lock = asyncio.Lock()
        self._cities: list[dict[str, Any]] | None = None
        self._cities_at = 0.0

    async def aclose(self) -> None:
        await self._client.aclose()

    # -- autenticacao ----------------------------------------------------

    async def _login(self) -> None:
        response = await self._client.post(
            "/auth/login",
            json={"email": self._email, "password": self._password},
        )
        if response.status_code != 201:
            raise FogoCruzadoError(f"Login falhou: status={response.status_code}")
        data = (response.json() or {}).get("data") or {}
        token = data.get("accessToken")
        if not token:
            raise FogoCruzadoError("Login nao retornou accessToken")
        try:
            ttl = float(data.get("expiresIn"))
        except (TypeError, ValueError):
            ttl = _DEFAULT_TOKEN_TTL_SECONDS
        self._token = token
        self._token_expiry = time.monotonic() + ttl

    def _token_valid(self) -> bool:
        return bool(self._token) and time.monotonic() < self._token_expiry - _TOKEN_REFRESH_MARGIN_SECONDS

    async def _ensure_token(self) -> str:
        if self._token_valid():
            return self._token  # type: ignore[return-value]
        async with self._auth_lock:
            if self._token_valid():
                return self._token  # type: ignore[return-value]
            await self._login()
            return self._token  # type: ignore[return-value]

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        token = await self._ensure_token()
        response = await self._client.get(
            path, params=params, headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 401:
            # Token rejeitado: forca novo login uma vez.
            self._token = None
            token = await self._ensure_token()
            response = await self._client.get(
                path, params=params, headers={"Authorization": f"Bearer {token}"}
            )
        return response

    # -- consultas -------------------------------------------------------

    async def get_cities(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        if self._cities is not None and now < self._cities_at + self._catalog_ttl:
            return self._cities
        response = await self._get("/cities")
        if response.status_code != 200:
            raise FogoCruzadoError(f"/cities status={response.status_code}")
        cities = (response.json() or {}).get("data") or []
        self._cities = cities
        self._cities_at = now
        return cities

    async def get_occurrences(
        self, params: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], dict[str, Any], datetime | None]:
        response = await self._get("/occurrences", params=params)
        if response.status_code != 200:
            raise FogoCruzadoError(f"/occurrences status={response.status_code}")
        payload = response.json() or {}
        data = payload.get("data") or []
        page_meta = payload.get("pageMeta") or {}
        last_update = parse_api_datetime(response.headers.get("x-last-update"))
        return data, page_meta, last_update

    async def probe(self) -> datetime | None:
        """Sonda de saude: confirma autenticacao e tenta ler a ultima atualizacao."""
        await self._ensure_token()
        try:
            _data, _meta, last_update = await self.get_occurrences(
                {"page": 1, "take": 1, "order": "DESC"}
            )
        except FogoCruzadoError:
            return None
        return last_update
