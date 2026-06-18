"""Output models for the MCP tools.

Tools return these models directly; FastMCP builds the schema and structured
JSON content from the Pydantic definitions. Field descriptions and Literal value
sets are part of the contract the calling agent reads, so they are written for the
agent: they explain what each field means and how to act on it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Reused value sets, declared once so the schema and the code agree.
EvidenceLevel = Literal[
    "no evidence",
    "no recent evidence",
    "low evidence",
    "moderate evidence",
    "high evidence",
]
ConfidenceLevel = Literal["low", "medium", "high"]
MatchQuality = Literal["exact", "approximate", "ambiguous"]
ResolutionStatus = Literal["resolved", "ambiguous", "approximate", "not_found"]
SpatialConcentration = Literal["concentrated", "localized", "dispersed", "indeterminate"]
RecencySignal = Literal["very recent", "recent", "cooling", "likely subsided"]
RelativeLevel = Literal["below", "typical", "above", "well above", "indeterminate"]
SourceState = Literal[
    "operational",
    "unavailable",
    "integrated",
    "validated, not integrated",
]


class SourceRef(BaseModel):
    """Reference to a data source used in a response."""

    name: str = Field(description='Human-readable source name, e.g. "Fogo Cruzado".')
    access_type: str = Field(
        description='How the source was accessed, e.g. "REST API (JWT)".'
    )
    queried_at: datetime = Field(
        description="UTC time this source was queried for this response."
    )
    last_update_time: datetime | None = Field(
        default=None,
        description="UTC time the source last updated its data, when it reports one.",
    )
    url: str | None = Field(default=None, description="Public source URL, when available.")


class RecentOccurrence(BaseModel):
    """Normalized recent occurrence.

    For safety, exact coordinates are intentionally omitted; neighborhood and
    regional labels carry the location context.
    """

    occurred_at: datetime | None = Field(
        default=None, description="UTC time the occurrence was reported, when known."
    )
    state: str | None = Field(default=None, description="State label, when known.")
    city: str | None = Field(default=None, description="City label, when known.")
    neighborhood: str | None = Field(
        default=None, description="Coarse neighborhood label; never an exact address."
    )
    sub_neighborhood: str | None = Field(
        default=None, description="Finer area label, when known; still coarse."
    )
    locality: str | None = Field(
        default=None, description="Named locality/community label, when known."
    )
    police_action: bool | None = Field(
        default=None, description="Whether the report indicates police action, when known."
    )
    agent_presence: bool | None = Field(
        default=None, description="Whether security-agent presence was reported, when known."
    )
    main_reason: str | None = Field(
        default=None, description="Reported main reason/context, when known."
    )
    victims_count: int = Field(default=0, description="Victims reported in this occurrence.")
    deaths_count: int = Field(default=0, description="Fatalities reported in this occurrence.")
    transport_interrupted: bool = Field(
        default=False,
        description="Whether public transport was reported interrupted nearby.",
    )
    massacre: bool = Field(
        default=False,
        description="Whether the source flagged this occurrence as a massacre (high severity).",
    )


class TerritorialContext(BaseModel):
    """Official IBGE territorial normalization for the requested city.

    Descriptive enrichment only: it does not change evidence or confidence. All
    values are resolved live from the IBGE API at query time (nothing hardcoded).
    """

    ibge_city_code: int | None = Field(
        default=None,
        description=(
            "Official 7-digit IBGE municipality code, resolved live. Join key for "
            "historical sources. Null if the city could not be resolved."
        ),
    )
    resolved_name: str | None = Field(
        default=None, description="Canonical municipality name as registered by IBGE."
    )
    uf: str | None = Field(
        default=None, description='Two-letter state abbreviation (UF), e.g. "RJ".'
    )
    macro_region: str | None = Field(
        default=None, description='Brazilian macro-region, e.g. "Sudeste".'
    )
    population: int | None = Field(
        default=None,
        description="Reserved; populated offline via SIDRA in a later tier. Currently null.",
    )
    match_quality: MatchQuality = Field(
        description=(
            "How reliably the requested name matched an official municipality. "
            '"exact": unique accent-insensitive name match. '
            '"approximate": partial/substring match. '
            '"ambiguous": the name maps to more than one municipality. If "ambiguous", '
            "ask the user for the state (UF) and query again before trusting the city."
        )
    )


class LocationCandidate(BaseModel):
    """One municipality that matched a location lookup."""

    ibge_city_code: int | None = Field(
        default=None, description="Official 7-digit IBGE municipality code, resolved live."
    )
    name: str | None = Field(default=None, description="Canonical municipality name (IBGE).")
    uf: str | None = Field(
        default=None, description='State abbreviation (UF), e.g. "RJ".'
    )
    macro_region: str | None = Field(
        default=None, description='Brazilian macro-region, e.g. "Sudeste".'
    )


class LocationResolution(BaseModel):
    """Result returned by `resolve_location`.

    A lookup-only tool: it turns a human city name into official IBGE
    candidates so the agent can disambiguate before querying activity. Codes are
    resolved live; pass the city name onward to other tools, not the code.
    """

    query: str = Field(description="The city name as requested.")
    uf_filter: str | None = Field(
        default=None, description="State hint applied to narrow the search, if any."
    )
    status: ResolutionStatus = Field(
        description=(
            '"resolved": one confident match (use candidates[0]). '
            '"ambiguous": several municipalities share the name—ask the user for the '
            "state (UF) and call again with uf, or let the user pick a candidate. "
            '"approximate": a single partial match—confirm it is the intended city. '
            '"not_found": nothing matched—check the spelling.'
        )
    )
    candidates: list[LocationCandidate] = Field(
        default_factory=list, description="Matching municipalities, best-effort ordered."
    )
    query_time: datetime = Field(description="UTC time this lookup was executed.")
    limitations: list[str] = Field(
        default_factory=list, description="Caveats about this lookup; relay to the user."
    )
    sources: list[SourceRef] = Field(
        default_factory=list, description="Attribution for the source consulted."
    )


class CorroboratingReport(BaseModel):
    """An official COR.Rio security/operations bulletin near the queried area.

    Independent context from a public source (Rio de Janeiro city only), filtered
    to police/security topics. It indicates that official activity was reported
    nearby in the same window; it does NOT confirm a specific occurrence. Phase A:
    descriptive only, does not change evidence or confidence.
    """

    title: str = Field(description="Bulletin headline, plain text.")
    area: str | None = Field(
        default=None, description="Location term the bulletin matched, when known."
    )
    summary: str | None = Field(
        default=None, description="Short plain-text excerpt; never the full article."
    )
    published_at: datetime | None = Field(
        default=None, description="UTC publication time, when known."
    )
    source: str = Field(default="COR.Rio", description='Always "COR.Rio".')
    url: str | None = Field(default=None, description="Link to the official bulletin.")


class IndicatorBaseline(BaseModel):
    """Historical levels for one ISP indicator in a municipality."""

    typical_monthly: float | None = Field(
        default=None, description="Average monthly count over the typical window (12 months)."
    )
    recent_monthly: float | None = Field(
        default=None, description="Average monthly count over the recent window (6 months)."
    )
    per_100k_annual: float | None = Field(
        default=None, description="Annualized rate per 100k inhabitants (typical window)."
    )
    percentile: float | None = Field(
        default=None,
        description="Rank in [0,1] of the per-100k rate across RJ municipalities (1 = highest).",
    )


class HistoricalBaseline(BaseModel):
    """ISP historical context for the area's chronic violence intensity.

    Descriptive (Phase A): a separate axis from the live signal. It never changes
    evidence or confidence, and it is ISP-internal (recent vs the area's own
    typical), never a same-unit comparison against the live Fogo Cruzado count.
    Rio de Janeiro state only.
    """

    source: str = Field(default="ISP Dados RJ", description='Always "ISP Dados RJ".')
    ibge_city_code: int | None = Field(default=None, description="Municipality IBGE code.")
    population: int | None = Field(default=None, description="Population used for per-100k (IBGE/SIDRA).")
    police_lethality: IndicatorBaseline = Field(
        description="Deaths by police intervention — the primary operation-lethality lens."
    )
    violent_lethality: IndicatorBaseline = Field(
        description="Overall violent lethality — context and an under-reporting cross-check."
    )
    relative_level: RelativeLevel = Field(
        description=(
            "Police lethality in the recent window vs the area's own typical level: "
            '"below"/"typical"/"above"/"well above". Chronic trend, not a live-event claim.'
        )
    )
    typical_window: str = Field(description="Label of the typical window, e.g. '12 months ending 2026-03'.")
    recent_window: str = Field(description="Label of the recent window, e.g. '6 months ending 2026-03'.")
    as_of: str | None = Field(default=None, description="Latest ISP period covered, e.g. '2026-03'.")
    note: str = Field(description="Plain-language summary and the under-reporting caveat.")


class OperationProfile(BaseModel):
    """Recent-intensity profile derived from Fogo Cruzado occurrences.

    Descriptive context (Phase A): it characterizes how intense/operation-like
    recent activity looks, without changing evidence or confidence. Spatial output
    is coarse by design; exact coordinates are never exposed.
    """

    massacre_flagged: bool = Field(
        description="Whether any occurrence in the window was flagged as a massacre."
    )
    distinct_police_units: int = Field(
        description=(
            "Number of distinct police units seen in the window. Several distinct "
            "units suggests a larger, coordinated operation. 0 when unreported."
        )
    )
    spatial_concentration: SpatialConcentration = Field(
        description=(
            'How clustered the occurrences are. "concentrated"/"localized"/"dispersed" '
            'by spread; "indeterminate" when too few are geocoded. Note: the source '
            'approximates coordinates, so "dispersed" is reliable but a tight cluster '
            "may be a geocoding artifact and is lower confidence."
        )
    )
    approx_spread_m: int | None = Field(
        default=None,
        description="Approximate spread (diameter) in meters, rounded coarse. Null if indeterminate.",
    )
    recency_signal: RecencySignal = Field(
        description=(
            "How current the activity looks, by age of the most recent occurrence: "
            '"very recent" -> "likely subsided". We cannot know when an operation '
            "ends; staleness only raises the chance it is over."
        )
    )
    note: str = Field(description="Plain-language summary of the profile and its caveats.")


class RecentActivityResult(BaseModel):
    """Result returned by `get_recent_activity`."""

    city: str = Field(description="Resolved city name used for the query.")
    region: str | None = Field(
        default=None, description="Neighborhood/region filter applied within the city, if any."
    )
    time_window: str = Field(
        description=(
            'Effective time window applied, e.g. "1h". May differ from the request '
            'if it was invalid (falls back to "1h") or capped (max "7d").'
        )
    )
    query_time: datetime = Field(description="UTC time this query was executed.")
    source_update_time: datetime | None = Field(
        default=None, description="UTC time the primary source last updated, when reported."
    )
    occurrence_count: int = Field(
        description="Occurrences within the window after region filtering."
    )
    newest_occurrence_age_minutes: float | None = Field(
        default=None,
        description="Age in minutes of the most recent occurrence, or null if none.",
    )
    activity_summary: str = Field(
        description="Short human-readable summary of the findings."
    )
    evidence_level: EvidenceLevel = Field(
        description=(
            "How much recent signal exists, from weakest to strongest. Independent "
            "from confidence_level; do not conflate them."
        )
    )
    confidence_level: ConfidenceLevel = Field(
        description=(
            "How reliable the evidence assessment is, given volume and recency. "
            "Independent from evidence_level."
        )
    )
    territorial_context: TerritorialContext | None = Field(
        default=None,
        description="Official IBGE normalization of the queried city; null if unavailable.",
    )
    corroborating_reports: list[CorroboratingReport] = Field(
        default_factory=list,
        description=(
            "Official COR.Rio security/operations bulletins that mention the same "
            "area within the window (Rio de Janeiro city only). Context that official "
            "activity was reported nearby—NOT confirmation of a specific occurrence. "
            "Present it as context; it does not change evidence or confidence. Empty "
            "for other cities or when nothing relevant matches."
        ),
    )
    operation_profile: OperationProfile | None = Field(
        default=None,
        description=(
            "Recent-intensity profile (massacre flag, distinct police units, spatial "
            "concentration, recency). Descriptive context; does not change evidence or "
            "confidence. Null when there are no occurrences in the window."
        ),
    )
    historical_baseline: HistoricalBaseline | None = Field(
        default=None,
        description=(
            "ISP chronic violence-intensity context for the area (Rio de Janeiro "
            "state only). Descriptive context on a separate axis; does not change "
            "evidence or confidence. Null outside RJ or when unavailable."
        ),
    )
    recent_occurrences: list[RecentOccurrence] = Field(
        default_factory=list,
        description="Normalized occurrences within the window (coarse location only).",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Caveats that bound this result. Always relay these to the user.",
    )
    sources: list[SourceRef] = Field(
        default_factory=list,
        description="Attribution for every source consulted, with timestamps.",
    )


class DataSourceStatus(BaseModel):
    """Operational status for one data source."""

    name: str = Field(description="Source name.")
    role: str = Field(description="What the source contributes to answers.")
    access_type: str = Field(description="How the source is accessed.")
    status: SourceState = Field(
        description=(
            '"operational"/"unavailable": integrated source that passed/failed a live '
            'health probe. "integrated": integrated but not probed this call. '
            '"validated, not integrated": catalogued, not yet used in answers.'
        )
    )
    coverage: str = Field(description="Geographic coverage of the source.")
    last_query_time: datetime | None = Field(
        default=None, description="UTC time this source was last probed/queried."
    )
    last_update_time: datetime | None = Field(
        default=None, description="UTC time the source last updated its data, when known."
    )
    known_limitations: list[str] = Field(
        default_factory=list, description="Known caveats for this source."
    )


class DataSourcesResult(BaseModel):
    """Result returned by `list_data_sources`."""

    sources: list[DataSourceStatus] = Field(
        description="One status entry per known source, integrated or catalogued."
    )
    query_time: datetime = Field(description="UTC time this listing was produced.")
    limitations: list[str] = Field(
        default_factory=list, description="Caveats about the listing as a whole."
    )
