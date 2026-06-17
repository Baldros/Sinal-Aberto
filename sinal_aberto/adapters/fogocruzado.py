"""Asynchronous adapter for the Fogo Cruzado API.

Encapsulates JWT authentication with in-memory token caching, city lookup with a
short catalog cache, and occurrence queries. MCP tools do not call the API
directly; they go through this adapter. Endpoint contracts are validated in
tests/integration/test_fogocruzado_api.py.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

# Safety margin used to refresh the token before the API expiration boundary.
_TOKEN_REFRESH_MARGIN_SECONDS = 30.0
_DEFAULT_TOKEN_TTL_SECONDS = 3600.0


def parse_api_datetime(value: str | None) -> datetime | None:
    """Convert an API timestamp into a timezone-aware datetime."""
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
    """Raised when the Fogo Cruzado API cannot be queried successfully."""


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

    # -- authentication --------------------------------------------------

    async def _login(self) -> None:
        """Authenticate once and store the token plus its monotonic expiry."""
        response = await self._client.post(
            "/auth/login",
            json={"email": self._email, "password": self._password},
        )
        if response.status_code != 201:
            raise FogoCruzadoError(f"Login failed: status={response.status_code}")
        data = (response.json() or {}).get("data") or {}
        token = data.get("accessToken")
        if not token:
            raise FogoCruzadoError("Login did not return accessToken")
        try:
            ttl = float(data.get("expiresIn"))
        except (TypeError, ValueError):
            ttl = _DEFAULT_TOKEN_TTL_SECONDS
        self._token = token
        self._token_expiry = time.monotonic() + ttl

    def _token_valid(self) -> bool:
        return bool(self._token) and time.monotonic() < self._token_expiry - _TOKEN_REFRESH_MARGIN_SECONDS

    async def _ensure_token(self) -> str:
        """Return a valid bearer token, serializing refreshes across coroutines."""
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
            # A rejected token gets one forced re-login before returning the response.
            self._token = None
            token = await self._ensure_token()
            response = await self._client.get(
                path, params=params, headers={"Authorization": f"Bearer {token}"}
            )
        return response

    # -- queries ---------------------------------------------------------

    async def get_cities(self) -> list[dict[str, Any]]:
        """Return the city catalog, using the short in-memory cache when fresh."""
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
        """Query occurrences and return rows, pagination metadata, and update time."""
        response = await self._get("/occurrences", params=params)
        if response.status_code != 200:
            raise FogoCruzadoError(f"/occurrences status={response.status_code}")
        payload = response.json() or {}
        data = payload.get("data") or []
        page_meta = payload.get("pageMeta") or {}
        last_update = parse_api_datetime(response.headers.get("x-last-update"))
        return data, page_meta, last_update

    async def probe(self) -> datetime | None:
        """Health probe: authenticate and try to read the latest update timestamp."""
        await self._ensure_token()
        try:
            _data, _meta, last_update = await self.get_occurrences(
                {"page": 1, "take": 1, "order": "DESC"}
            )
        except FogoCruzadoError:
            return None
        return last_update
