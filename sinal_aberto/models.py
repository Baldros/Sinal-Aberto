"""Modelos de saida das ferramentas MCP.

Sao retornados diretamente pelas tools; o FastMCP gera o schema e o conteudo
estruturado em JSON a partir destes modelos Pydantic.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    """Referencia de fonte usada em uma resposta."""

    name: str
    access_type: str
    queried_at: datetime
    last_update_time: datetime | None = None
    url: str | None = None


class RecentOccurrence(BaseModel):
    """Ocorrencia recente normalizada.

    Por seguranca, nao expoe coordenadas exatas: usa rotulos de bairro/regiao.
    """

    occurred_at: datetime | None = None
    state: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    sub_neighborhood: str | None = None
    locality: str | None = None
    police_action: bool | None = None
    agent_presence: bool | None = None
    main_reason: str | None = None
    victims_count: int = 0
    deaths_count: int = 0
    transport_interrupted: bool = False


class RecentActivityResult(BaseModel):
    """Resultado de `get_recent_activity`."""

    city: str
    region: str | None = None
    time_window: str
    query_time: datetime
    source_update_time: datetime | None = None
    occurrence_count: int
    newest_occurrence_age_minutes: float | None = None
    activity_summary: str
    evidence_level: str
    confidence_level: str
    recent_occurrences: list[RecentOccurrence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class DataSourceStatus(BaseModel):
    """Estado operacional de uma fonte de dados."""

    name: str
    role: str
    access_type: str
    status: str
    coverage: str
    last_query_time: datetime | None = None
    last_update_time: datetime | None = None
    known_limitations: list[str] = Field(default_factory=list)


class DataSourcesResult(BaseModel):
    """Resultado de `list_data_sources`."""

    sources: list[DataSourceStatus]
    query_time: datetime
    limitations: list[str] = Field(default_factory=list)
