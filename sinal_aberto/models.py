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
