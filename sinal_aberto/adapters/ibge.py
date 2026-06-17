"""Asynchronous adapter for the IBGE Localidades API.

Official territorial-normalization source. Unlike Fogo Cruzado, this API is
public and does not require authentication. Municipal metadata changes rarely,
so the full municipality catalog is kept in a long in-memory cache, without a
background job or database. Tools do not call the API directly; they go through
this adapter. The contract is validated in
tests/integration/test_ibge_localidades.py.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

# Municipal metadata is effectively static for this workflow, so a one-day cache is safe.
_DEFAULT_CATALOG_TTL_SECONDS = 86_400.0


class IbgeError(RuntimeError):
    """Raised when the IBGE Localidades API cannot be queried successfully."""


class IbgeLocalidadesClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 20.0,
        catalog_ttl: float = _DEFAULT_CATALOG_TTL_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._catalog_ttl = catalog_ttl
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport
        )
        self._municipalities: list[dict[str, Any]] | None = None
        self._municipalities_at = 0.0

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_municipalities(self) -> list[dict[str, Any]]:
        """Return the full Brazilian municipality catalog with a long cache.

        Each item includes the territorial hierarchy (municipality >
        micro-region > meso-region > state > region), which supplies the IBGE
        code, state, and macro-region.
        """
        now = time.monotonic()
        if (
            self._municipalities is not None
            and now < self._municipalities_at + self._catalog_ttl
        ):
            return self._municipalities
        response = await self._client.get("/municipios")
        if response.status_code != 200:
            raise IbgeError(f"/municipios status={response.status_code}")
        municipalities = response.json() or []
        if not isinstance(municipalities, list):
            raise IbgeError("/municipios did not return a list")
        self._municipalities = municipalities
        self._municipalities_at = now
        return municipalities

    async def probe(self) -> None:
        """Health probe: confirm the municipality catalog responds with data."""
        municipalities = await self.get_municipalities()
        if not municipalities:
            raise IbgeError("/municipios returned an empty list")
