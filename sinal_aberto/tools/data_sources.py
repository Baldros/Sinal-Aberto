"""`list_data_sources` tool implementation.

Lists Sinal Aberto sources and their status. Fogo Cruzado and IBGE Localidades
are integrated and receive live health probes; the remaining sources are listed
as validated but not yet integrated, reflecting
docs/validacao-fontes-secundarias.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..adapters.cor_rio import CorRioClient
from ..adapters.fogocruzado import FogoCruzadoClient
from ..adapters.ibge import IbgeLocalidadesClient
from ..models import DataSourcesResult, DataSourceStatus

# Static catalog for auxiliary sources that were validated but are not integrated yet.
# IBGE Localidades (Tier 1) and COR.Rio (Tier 3) are no longer here: both promoted.
_SECONDARY: tuple[dict, ...] = (
    {
        "name": "IBGE Malhas",
        "role": "official geometries",
        "access_type": "API REST GeoJSON",
        "coverage": "Brazil",
        "known_limitations": [
            "HEAD returns 405; use GET.",
            "Validated; not used in responses yet.",
        ],
    },
    {
        "name": "ISP Dados RJ",
        "role": "official public-safety history for RJ",
        "access_type": "CKAN + download CSV/SHP/KML",
        "coverage": "Rio de Janeiro state",
        "known_limitations": [
            "Historical/aggregate data, not real time.",
            "Validated; not used in responses yet.",
        ],
    },
    {
        "name": "SINESP/MJSP",
        "role": "aggregate national history",
        "access_type": "CKAN + download ZIP/XLSX",
        "coverage": "Brazil",
        "known_limitations": [
            "Aggregate source; not suitable for ongoing events.",
            "Validated; not used in responses yet.",
        ],
    },
    {
        "name": "DATA.RIO (ArcGIS)",
        "role": "urban layers for Rio de Janeiro city",
        "access_type": "ArcGIS REST/FeatureServer",
        "coverage": "Rio de Janeiro city",
        "known_limitations": [
            "Logical errors arrive as HTTP 200 plus an 'error' key.",
            "Validated; not used in responses yet.",
        ],
    },
    {
        "name": "GTFS Rio",
        "role": "mobility context for bus/BRT routes and stops",
        "access_type": "ZIP download (static GTFS)",
        "coverage": "Rio de Janeiro city",
        "known_limitations": [
            "Static GTFS, not real time.",
            "Validated; not used in responses yet.",
        ],
    },
    {
        "name": "GPS SPPO",
        "role": "operational mobility context",
        "access_type": "REST with time-window filter",
        "coverage": "Rio de Janeiro city",
        "known_limitations": [
            "Content-Type is text/html while the body is JSON.",
            "Requires a short time window.",
            "Validated; not used in responses yet.",
        ],
    },
)


async def list_data_sources(
    client: FogoCruzadoClient,
    territory: IbgeLocalidadesClient | None = None,
    corroboration: CorRioClient | None = None,
) -> DataSourcesResult:
    """Probe integrated sources and return the full source catalog."""
    query_time = datetime.now(timezone.utc)
    limitations = [
        "Integrated into responses: Fogo Cruzado (occurrences), IBGE Localidades "
        "(territorial normalization), and COR.Rio (official corroboration, Rio "
        "only). Other sources are validated but not queried in real time yet."
    ]

    try:
        last_update = await client.probe()
        fogo_status = "operational"
    except Exception:  # noqa: BLE001 - any probe failure becomes unavailable status
        last_update = None
        fogo_status = "unavailable"
        limitations.append(
            "Fogo Cruzado did not respond to the health probe at query time."
        )

    sources = [
        DataSourceStatus(
            name="Fogo Cruzado",
            role="primary source for recent armed occurrences",
            access_type="API REST (JWT)",
            status=fogo_status,
            coverage="Metropolitan regions of Rio de Janeiro, Recife, Bahia, and Para",
            last_query_time=query_time,
            last_update_time=last_update,
            known_limitations=[
                "Covers reported shootings/gunfire; it is not a complete operations radar.",
                "Operations without gunfire or reports may not appear.",
            ],
        )
    ]

    ibge_status = "integrated"
    if territory is not None:
        try:
            await territory.probe()
            ibge_status = "operational"
        except Exception:  # noqa: BLE001 - any probe failure becomes unavailable status
            ibge_status = "unavailable"
            limitations.append(
                "IBGE Localidades did not respond to the health probe at query time."
            )
    sources.append(
        DataSourceStatus(
            name="IBGE Localidades",
            role="official territorial normalization (Tier 1)",
            access_type="API REST JSON",
            status=ibge_status,
            coverage="Brazil",
            last_query_time=query_time,
            known_limitations=[
                "Descriptive enrichment: resolves IBGE code/state/macro-region, "
                "without changing evidence or confidence.",
            ],
        )
    )

    cor_rio_status = "integrated"
    if corroboration is not None:
        try:
            await corroboration.probe()
            cor_rio_status = "operational"
        except Exception:  # noqa: BLE001 - any probe failure becomes unavailable status
            cor_rio_status = "unavailable"
            limitations.append(
                "COR.Rio did not respond to the health probe at query time."
            )
    sources.append(
        DataSourceStatus(
            name="COR.Rio",
            role="official textual corroboration (Tier 3)",
            access_type="WordPress REST JSON",
            status=cor_rio_status,
            coverage="Rio de Janeiro city",
            last_query_time=query_time,
            known_limitations=[
                "Requires browser-like headers; the WAF returns 403 without them.",
                "Text corroboration only; adds context, not evidence or confidence "
                "(Phase A: descriptive).",
            ],
        )
    )

    for source in _SECONDARY:
        sources.append(DataSourceStatus(status="validated, not integrated", **source))

    return DataSourcesResult(
        sources=sources, query_time=query_time, limitations=limitations
    )
