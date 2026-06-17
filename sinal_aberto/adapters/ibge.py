"""Adaptador assincrono da API IBGE Localidades.

Fonte de normalizacao territorial oficial. Diferente do Fogo Cruzado, e publica e
sem autenticacao: a malha municipal quase nao muda, entao o catalogo inteiro de
municipios fica num cache longo em memoria (sem job, sem banco). As tools nao
falam diretamente com a API: passam por aqui. Contrato validado em
tests/integration/test_ibge_localidades.py.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

# A malha municipal praticamente nao muda; um dia de cache e folgado.
_DEFAULT_CATALOG_TTL_SECONDS = 86_400.0


class IbgeError(RuntimeError):
    """Falha ao consultar a API IBGE Localidades."""


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
        self._municipios: list[dict[str, Any]] | None = None
        self._municipios_at = 0.0

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_municipios(self) -> list[dict[str, Any]]:
        """Catalogo completo de municipios do Brasil, com cache longo.

        Cada item traz a hierarquia territorial (municipio > microrregiao >
        mesorregiao > UF > regiao), de onde extraimos codigo IBGE, UF e macrorregiao.
        """
        now = time.monotonic()
        if self._municipios is not None and now < self._municipios_at + self._catalog_ttl:
            return self._municipios
        response = await self._client.get("/municipios")
        if response.status_code != 200:
            raise IbgeError(f"/municipios status={response.status_code}")
        municipios = response.json() or []
        if not isinstance(municipios, list):
            raise IbgeError("/municipios nao retornou uma lista")
        self._municipios = municipios
        self._municipios_at = now
        return municipios

    async def probe(self) -> None:
        """Sonda de saude: confirma que o catalogo de municipios responde."""
        municipios = await self.get_municipios()
        if not municipios:
            raise IbgeError("/municipios retornou vazio")
