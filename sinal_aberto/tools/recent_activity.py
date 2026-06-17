"""`get_recent_activity` tool implementation.

Queries recent signs of armed or police activity in a city and returns a
traceable summary. The API filters occurrences by date with day-level
granularity, so this module fetches recent records for the period and refines
the exact minute/hour window in application code.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..adapters.cor_rio import CorRioClient
from ..adapters.fogocruzado import FogoCruzadoClient
from ..adapters.ibge import IbgeLocalidadesClient
from ..models import (
    CorroboratingReport,
    RecentActivityResult,
    RecentOccurrence,
    SourceRef,
    TerritorialContext,
)
from .corroboration import collect_terms, match_reports
from .territory import resolve_territory, slugify

SOURCE_URL = "https://api.fogocruzado.org.br/"
IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
COR_RIO_URL = "https://cor.rio/"
COR_RIO_IBGE_CODE = 3304557
MAX_WINDOW = timedelta(days=7)
MAX_FETCH = 50
_WINDOW_RE = re.compile(r"^\s*(\d+)\s*([mhd])\s*$", re.IGNORECASE)
_DEATH_TOKENS = ("mort", "obito", "\u00f3bito", "dead", "fatal")


def _parse_window(value: str | None) -> tuple[timedelta, str, bool]:
    """Parse compact time windows such as 30m, 1h, and 2d."""
    match = _WINDOW_RE.match(value or "")
    if not match:
        return timedelta(hours=1), "1h", False
    amount = int(match.group(1))
    unit = match.group(2).lower()
    delta = {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
    }[unit]
    return delta, f"{amount}{unit}", True


def _label(value: Any) -> str | None:
    """Extract the human-readable API label from a reference object or raw string."""
    if isinstance(value, dict):
        return value.get("name")
    if isinstance(value, str):
        return value or None
    return None


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an API datetime and ensure the result is timezone-aware."""
    try:
        parsed = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize(occ: dict[str, Any]) -> RecentOccurrence:
    """Convert a raw Fogo Cruzado occurrence into the public MCP response shape."""
    context = occ.get("contextInfo") or {}
    victims = occ.get("victims") or []
    deaths = 0
    for victim in victims:
        situation = (victim.get("situation") or "").lower()
        if victim.get("deathDate") or any(token in situation for token in _DEATH_TOKENS):
            deaths += 1
    transports = occ.get("transports") or []
    return RecentOccurrence(
        occurred_at=_parse_dt(occ.get("date")),
        state=_label(occ.get("state")),
        city=_label(occ.get("city")),
        neighborhood=_label(occ.get("neighborhood")),
        sub_neighborhood=_label(occ.get("subNeighborhood")),
        locality=_label(occ.get("locality")),
        police_action=occ.get("policeAction"),
        agent_presence=occ.get("agentPresence"),
        main_reason=_label(context.get("mainReason")),
        victims_count=len(victims),
        deaths_count=deaths,
        transport_interrupted=any(t.get("interruptedTransport") for t in transports),
    )


def _assess(
    recent: list[RecentOccurrence], query_time: datetime
) -> tuple[str, str, str]:
    count = len(recent)
    if count == 0:
        return "no recent evidence", "low", "No recent records in the requested window."

    ages = [o.occurred_at for o in recent if o.occurred_at]
    newest = max(ages) if ages else None
    age_min = (query_time - newest).total_seconds() / 60.0 if newest else None
    fresh = age_min is not None and age_min <= 60

    police = sum(1 for o in recent if o.police_action)
    victims = sum(o.victims_count for o in recent)
    deaths = sum(o.deaths_count for o in recent)

    if count >= 5 or (count >= 2 and fresh):
        evidence = "high evidence"
    elif count >= 2 or (age_min is not None and age_min <= 180):
        evidence = "moderate evidence"
    else:
        evidence = "low evidence"

    if count >= 5 and fresh:
        confidence = "high"
    elif count >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    parts = [f"{count} recent record(s)"]
    if age_min is not None:
        parts.append(f"latest ~{int(age_min)} min ago")
    if police:
        parts.append(f"{police} with police action")
    if victims:
        victim_part = f"{victims} victim(s)"
        if deaths:
            victim_part += f", {deaths} death(s)"
        parts.append(victim_part)
    summary = "; ".join(parts) + "."
    return evidence, confidence, summary


async def _resolve_territory(
    territory: IbgeLocalidadesClient | None,
    *,
    name: str,
    uf: str | None,
    query_time: datetime,
    sources: list[SourceRef],
    limitations: list[str],
) -> TerritorialContext | None:
    """Resolve optional IBGE territorial enrichment without blocking the tool.

    Source failures or missing data become a null field plus a limitation; they
    never fail the main activity query. The enrichment is descriptive and does
    not change evidence or confidence.
    """
    if territory is None:
        return None
    try:
        municipalities = await territory.get_municipalities()
    except Exception:  # noqa: BLE001 - optional enrichment degrades without failing
        limitations.append(
            "Territorial normalization (IBGE) unavailable; official code not resolved."
        )
        return None

    context = resolve_territory(municipalities, name, uf=uf)
    if context is None:
        limitations.append(
            "Could not resolve the official IBGE code for the requested city."
        )
        return None

    sources.append(
        SourceRef(
            name="IBGE Localidades",
            access_type="API REST JSON",
            queried_at=query_time,
            url=IBGE_URL,
        )
    )
    if context.match_quality == "ambiguous":
        limitations.append(
            "Territorial normalization is ambiguous; verify the resolved city state."
        )
    return context


async def _corroborate(
    corroboration: CorRioClient | None,
    *,
    is_rio: bool,
    region: str | None,
    occurrences: list[RecentOccurrence],
    window: timedelta,
    query_time: datetime,
    sources: list[SourceRef],
    limitations: list[str],
) -> list[CorroboratingReport]:
    """Optional COR.Rio corroboration, isolated and failure-tolerant.

    Rio de Janeiro only. Descriptive (Phase A): does not change evidence or
    confidence. An unavailable source, or nothing matching, degrades to an empty
    list; the main response never breaks.
    """
    if corroboration is None or not is_rio:
        return []
    terms = collect_terms(region, occurrences)
    if not terms:
        return []
    try:
        posts = await corroboration.get_recent_posts()
    except Exception:  # noqa: BLE001 - corroboration is optional; never breaks the tool
        limitations.append(
            "COR.Rio corroboration unavailable; official bulletins were not checked."
        )
        return []

    max_age = max(window, timedelta(hours=24))
    reports = match_reports(posts, terms, now=query_time, max_age=max_age, limit=5)
    if not reports:
        return []

    sources.append(
        SourceRef(
            name="COR.Rio",
            access_type="WordPress REST JSON",
            queried_at=query_time,
            url=COR_RIO_URL,
        )
    )
    limitations.append(
        "COR.Rio bulletins are official context about operations near the queried "
        "area; they do not confirm the specific occurrences and do not change the "
        "assessment."
    )
    if window < timedelta(hours=24):
        limitations.append(
            "Corroboration considers COR.Rio bulletins from the last 24h, which may "
            "be wider than the activity window."
        )
    return reports


async def get_recent_activity(
    client: FogoCruzadoClient,
    *,
    city: str,
    region: str | None = None,
    time_window: str = "1h",
    territory: IbgeLocalidadesClient | None = None,
    corroboration: CorRioClient | None = None,
) -> RecentActivityResult:
    """Fetch, filter, normalize, and assess recent Fogo Cruzado activity."""
    query_time = datetime.now(timezone.utc)
    window, window_label, ok = _parse_window(time_window)
    limitations: list[str] = []
    if not ok:
        limitations.append(
            f"time_window '{time_window}' is invalid; using 1h. Use formats like 30m, 1h, 24h."
        )
    if window > MAX_WINDOW:
        window, window_label = MAX_WINDOW, "7d"
        limitations.append("Time window capped at 7d in this version.")
    cutoff = query_time - window

    sources = [
        SourceRef(
            name="Fogo Cruzado",
            access_type="API REST (JWT)",
            queried_at=query_time,
            url=SOURCE_URL,
        )
    ]

    # City matching stays permissive for user input, but ambiguity is surfaced.
    cities = await client.get_cities()
    normalized_city = slugify(city)
    exact = [c for c in cities if slugify(c.get("name")) == normalized_city]
    matches = exact or [
        c for c in cities if normalized_city in slugify(c.get("name"))
    ]

    if not matches:
        return RecentActivityResult(
            city=city,
            region=region,
            time_window=window_label,
            query_time=query_time,
            occurrence_count=0,
            activity_summary=f"City '{city}' was not found in the Fogo Cruzado catalog.",
            evidence_level="no evidence",
            confidence_level="low",
            limitations=limitations
            + ["City not found; verify the name or the source coverage."],
            sources=sources,
        )

    if len(matches) > 1:
        candidates = sorted(
            {f"{c.get('name')} ({_label(c.get('state'))})" for c in matches}
        )[:5]
        limitations.append(
            "More than one city matches '"
            f"{city}'. Using the first one; specify the region/state. "
            f"Candidates: {', '.join(candidates)}."
        )

    target = matches[0]
    territorial_context = await _resolve_territory(
        territory,
        name=_label(target.get("name")) or city,
        uf=_label(target.get("state")),
        query_time=query_time,
        sources=sources,
        limitations=limitations,
    )

    params: dict[str, Any] = {
        "page": 1,
        "take": MAX_FETCH,
        "order": "DESC",
        "idCities": target.get("id"),
        "initialdate": cutoff.date().isoformat(),
        "finaldate": query_time.date().isoformat(),
    }
    state_id = (target.get("state") or {}).get("id")
    if state_id:
        params["idState"] = state_id

    data, page_meta, last_update = await client.get_occurrences(params)
    sources[0].last_update_time = last_update

    # The API may return a whole date range; this enforces the exact time window.
    recent: list[RecentOccurrence] = []
    for occ in data:
        occurred_at = _parse_dt(occ.get("date"))
        if occurred_at is not None and occurred_at >= cutoff:
            recent.append(_normalize(occ))

    region_filter = (region or "").strip().casefold()
    if region_filter:
        before = len(recent)
        recent = [
            o
            for o in recent
            if any(
                region_filter in (label or "").casefold()
                for label in (o.neighborhood, o.sub_neighborhood, o.locality)
            )
        ]
        if before and not recent:
            limitations.append(
                f"No recent records in region '{region}' within the requested window."
            )

    if page_meta.get("hasNextPage"):
        limitations.append(
            f"More than {MAX_FETCH} occurrences in the period; showing the most recent ones."
        )

    is_rio = (
        territorial_context is not None
        and territorial_context.ibge_city_code == COR_RIO_IBGE_CODE
    ) or slugify(_label(target.get("name")) or city) == "rio de janeiro"
    corroborating_reports = await _corroborate(
        corroboration,
        is_rio=is_rio,
        region=region,
        occurrences=recent,
        window=window,
        query_time=query_time,
        sources=sources,
        limitations=limitations,
    )

    evidence, confidence, summary = _assess(recent, query_time)

    newest_age = None
    ages = [o.occurred_at for o in recent if o.occurred_at]
    if ages:
        newest_age = round((query_time - max(ages)).total_seconds() / 60.0, 1)

    limitations.append(
        "Evidence/confidence levels are preliminary heuristics; they do not "
        "represent calibrated probability."
    )
    limitations.append(
        "The source covers reported shootings/gunfire; unreported operations "
        "may not appear."
    )

    return RecentActivityResult(
        city=_label(target.get("name")) or city,
        region=region,
        time_window=window_label,
        query_time=query_time,
        source_update_time=last_update,
        occurrence_count=len(recent),
        newest_occurrence_age_minutes=newest_age,
        activity_summary=summary,
        evidence_level=evidence,
        confidence_level=confidence,
        territorial_context=territorial_context,
        corroborating_reports=corroborating_reports,
        recent_occurrences=recent,
        limitations=limitations,
        sources=sources,
    )
