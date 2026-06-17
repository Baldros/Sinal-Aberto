"""Sinal Aberto MCP server.

Exposes the query tools through FastMCP using Streamable HTTP. Tools return
Pydantic models, which FastMCP serializes as structured JSON content.

Local execution from the repository root:

    ./.venv/Scripts/python.exe -m sinal_aberto.server
"""

from __future__ import annotations

from fastmcp import FastMCP

from .adapters.fogocruzado import FogoCruzadoClient
from .adapters.ibge import IbgeLocalidadesClient
from .config import get_settings
from .models import DataSourcesResult, RecentActivityResult
from .tools.data_sources import list_data_sources as _list_data_sources
from .tools.recent_activity import get_recent_activity as _get_recent_activity

mcp = FastMCP(
    "sinal-aberto",
    instructions=(
        "Sinal Aberto answers questions about recent signs of armed or police "
        "activity in Brazil, drawing on the Fogo Cruzado API and official "
        "reference data (IBGE).\n\n"
        "How to use these tools:\n"
        "- Call get_recent_activity with a human city name (and optional "
        "neighborhood and time window). The server resolves all official "
        "identifiers internally; never invent or pass numeric codes.\n"
        "- Read territorial_context.match_quality. If it is 'ambiguous', the city "
        "name maps to more than one municipality: ask the user for the state (UF) "
        "and query again before trusting the result.\n"
        "- evidence_level (how much signal) and confidence_level (how sure) are "
        "independent; never conflate them.\n"
        "- Always relay the 'limitations' to the user, and cite the sources.\n"
        "- Reply in the user's language; tool text is English but content should be "
        "presented in whatever language the user speaks.\n\n"
        "Safety: express evidence and uncertainty, never absolute claims. Do not "
        "provide routes, evasion guidance, agent-approach guidance, exact "
        "coordinates, or any tactical decision support."
    ),
)

_client: FogoCruzadoClient | None = None
_ibge_client: IbgeLocalidadesClient | None = None


def _get_client() -> FogoCruzadoClient:
    """Create the Fogo Cruzado client lazily so tests can import the server offline."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = FogoCruzadoClient(
            base_url=settings.fogocruzado_base_url,
            email=settings.fogocruzado_email,
            password=settings.fogocruzado_password,
            timeout=settings.http_timeout,
            catalog_ttl=settings.catalog_cache_ttl,
        )
    return _client


def _get_ibge_client() -> IbgeLocalidadesClient:
    """Create the IBGE client lazily and share its catalog cache across calls."""
    global _ibge_client
    if _ibge_client is None:
        settings = get_settings()
        _ibge_client = IbgeLocalidadesClient(
            base_url=settings.ibge_base_url,
            timeout=settings.http_timeout,
            catalog_ttl=settings.ibge_cache_ttl,
        )
    return _ibge_client


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def get_recent_activity(
    city: str,
    region: str | None = None,
    time_window: str = "1h",
) -> RecentActivityResult:
    """Query recent signs of armed or police activity in a Brazilian city.

    Returns a traceable summary: occurrence count, evidence and confidence levels,
    normalized occurrences by neighborhood/region (never exact coordinates),
    official IBGE territorial context, source attribution, and limitations.

    Agent guidance:
    - Pass a human city name; the server resolves official identifiers internally.
      Never invent or pass numeric codes.
    - Check territorial_context.match_quality. If "ambiguous", ask the user for the
      state (UF) and call again before trusting the result.
    - evidence_level (how much signal) and confidence_level (how sure) are
      independent. Always relay 'limitations' to the user.
    - Express evidence and uncertainty, never certainty. Do not provide routes,
      evasion, agent-approach, or tactical guidance.

    Args:
        city: City name, for example "Rio de Janeiro" or "Recife".
        region: Optional neighborhood or region to filter within the city.
        time_window: Recent window, for example "30m", "1h", "6h", "24h" (max "7d").
    """
    return await _get_recent_activity(
        _get_client(),
        city=city,
        region=region,
        time_window=time_window,
        territory=_get_ibge_client(),
    )


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def list_data_sources() -> DataSourcesResult:
    """List Sinal Aberto data sources and their operational status.

    Use this to explain coverage and freshness, or to check availability before
    relying on a source. Fogo Cruzado and IBGE Localidades are integrated and
    receive a live health probe; the remaining auxiliary sources are catalogued as
    validated but not yet integrated, matching the current system state. The
    'status' field of each entry tells the difference.
    """
    return await _list_data_sources(_get_client(), territory=_get_ibge_client())


def main() -> None:
    settings = get_settings()
    mcp.run(transport="http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
