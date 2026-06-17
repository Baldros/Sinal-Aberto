"""`resolve_location` tool.

Looks up the official IBGE municipality for a human city name and returns the
candidates so the calling agent can disambiguate before querying activity. This
is the dedicated lookup the agent uses when a name is ambiguous (or when
get_recent_activity reports match_quality="ambiguous"). Codes are resolved live
from the IBGE catalog; nothing is hardcoded.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..adapters.ibge import IbgeLocalidadesClient
from ..models import LocationCandidate, LocationResolution, SourceRef
from .territory import find_candidates, municipality_summary

IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
MAX_CANDIDATES = 10


async def resolve_location(
    territory: IbgeLocalidadesClient,
    *,
    name: str,
    uf: str | None = None,
) -> LocationResolution:
    query_time = datetime.now(timezone.utc)

    try:
        municipalities = await territory.get_municipalities()
    except Exception:  # noqa: BLE001 - lookup degrades gracefully, never raises
        return LocationResolution(
            query=name,
            uf_filter=uf,
            status="not_found",
            candidates=[],
            query_time=query_time,
            limitations=["IBGE Localidades unavailable; could not resolve the location."],
            sources=[],
        )

    sources = [
        SourceRef(
            name="IBGE Localidades",
            access_type="REST API JSON",
            queried_at=query_time,
            url=IBGE_URL,
        )
    ]
    matches, tier = find_candidates(municipalities, name, uf)
    limitations: list[str] = []

    if not matches:
        status = "not_found"
        limitations.append(
            "No municipality matched; check the spelling or try a nearby city."
        )
    elif len(matches) > 1:
        status = "ambiguous"
        limitations.append(
            "Multiple municipalities share this name; pass 'uf' (state) to "
            "disambiguate, or ask the user to choose a candidate."
        )
    elif tier == "approximate":
        status = "approximate"
        limitations.append(
            "Only a partial (substring) match was found; confirm it is the intended city."
        )
    else:
        status = "resolved"

    if len(matches) > MAX_CANDIDATES:
        limitations.append(
            f"More than {MAX_CANDIDATES} matches; showing the first {MAX_CANDIDATES}."
        )

    candidates = [
        LocationCandidate(**municipality_summary(m)) for m in matches[:MAX_CANDIDATES]
    ]
    return LocationResolution(
        query=name,
        uf_filter=uf,
        status=status,
        candidates=candidates,
        query_time=query_time,
        limitations=limitations,
        sources=sources,
    )
