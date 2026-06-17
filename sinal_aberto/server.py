"""Sinal Aberto MCP server.

Exposes the query tools through FastMCP using Streamable HTTP. Tools return
Pydantic models, which FastMCP serializes as structured JSON content.

Local execution from the repository root:

    ./.venv/Scripts/python.exe -m sinal_aberto.server
"""

from __future__ import annotations

from fastmcp import FastMCP

from .adapters.cor_rio import CorRioClient
from .adapters.fogocruzado import FogoCruzadoClient
from .adapters.ibge import IbgeLocalidadesClient
from .config import get_settings
from .models import DataSourcesResult, LocationResolution, RecentActivityResult
from .tools.baseline import BaselineStore
from .tools.data_sources import list_data_sources as _list_data_sources
from .tools.locations import resolve_location as _resolve_location
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
        "name maps to more than one municipality: call resolve_location to list the "
        "candidates, ask the user for the state (UF), and query again.\n"
        "- Use resolve_location whenever a place name may be ambiguous, to turn a "
        "name into the official municipality before querying activity.\n"
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
_cor_rio_client: CorRioClient | None = None
_baseline_store: BaselineStore | None = None


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


def _get_cor_rio_client() -> CorRioClient:
    """Create the COR.Rio client lazily and share its short cache across calls."""
    global _cor_rio_client
    if _cor_rio_client is None:
        settings = get_settings()
        _cor_rio_client = CorRioClient(
            base_url=settings.cor_rio_base_url,
            timeout=settings.http_timeout,
            cache_ttl=settings.cor_rio_cache_ttl,
        )
    return _cor_rio_client


def _get_baseline_store() -> BaselineStore:
    """Load the prepared ISP baseline once; degrades to empty if the file is absent."""
    global _baseline_store
    if _baseline_store is None:
        _baseline_store = BaselineStore()
    return _baseline_store


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
    - Check territorial_context.match_quality. If "ambiguous", call resolve_location
      to list candidates, ask the user for the state (UF), and call again.
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
        corroboration=_get_cor_rio_client(),
        baseline=_get_baseline_store(),
    )


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def resolve_location(name: str, uf: str | None = None) -> LocationResolution:
    """Resolve a Brazilian city name to its official IBGE municipality candidates.

    Lookup-only: it does not return activity data, just the official identity of a
    place so you can disambiguate before calling get_recent_activity.

    Agent guidance:
    - Use this when a city name might be ambiguous, or when get_recent_activity
      returns territorial_context.match_quality "ambiguous".
    - If status is "ambiguous", show the candidates to the user or pass 'uf' (the
      state) and call again; do not guess.
    - Codes are resolved live. Pass the city name (and state) onward to other
      tools, never a hardcoded code.

    Args:
        name: City name to resolve, for example "Bom Jesus".
        uf: Optional state to disambiguate, abbreviation or name, e.g. "RS" or
            "Rio Grande do Sul".
    """
    return await _resolve_location(_get_ibge_client(), name=name, uf=uf)


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def list_data_sources() -> DataSourcesResult:
    """List Sinal Aberto data sources and their operational status.

    Use this to explain coverage and freshness, or to check availability before
    relying on a source. Fogo Cruzado and IBGE Localidades are integrated and
    receive a live health probe; the remaining auxiliary sources are catalogued as
    validated but not yet integrated, matching the current system state. The
    'status' field of each entry tells the difference.
    """
    return await _list_data_sources(
        _get_client(),
        territory=_get_ibge_client(),
        corroboration=_get_cor_rio_client(),
    )


def main() -> None:
    settings = get_settings()
    mcp.run(transport="http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
