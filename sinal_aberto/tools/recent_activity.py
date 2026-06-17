"""Ferramenta `get_recent_activity`.

Consulta sinais recentes de atividade armada/policial em uma cidade e retorna um
resumo rastreavel. A API filtra ocorrencias por data (granularidade de dia), entao
buscamos as mais recentes do periodo e refinamos a janela exata (minutos/horas) no
proprio codigo.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from ..adapters.fogocruzado import FogoCruzadoClient
from ..adapters.ibge import IbgeLocalidadesClient
from ..models import RecentActivityResult, RecentOccurrence, SourceRef, TerritorialContext
from .territory import resolve_territory, slugify

FONTE_URL = "https://api.fogocruzado.org.br/"
IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
MAX_WINDOW = timedelta(days=7)
MAX_FETCH = 50
_WINDOW_RE = re.compile(r"^\s*(\d+)\s*([mhd])\s*$", re.IGNORECASE)
_DEATH_TOKENS = ("mort", "obito", "óbito", "dead", "fatal")


def _parse_window(value: str | None) -> tuple[timedelta, str, bool]:
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
    if isinstance(value, dict):
        return value.get("name")
    if isinstance(value, str):
        return value or None
    return None


def _parse_dt(value: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize(occ: dict[str, Any]) -> RecentOccurrence:
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
        return "sem evidencia recente", "baixa", "Nenhum registro recente na janela consultada."

    ages = [o.occurred_at for o in recent if o.occurred_at]
    newest = max(ages) if ages else None
    age_min = (query_time - newest).total_seconds() / 60.0 if newest else None
    fresh = age_min is not None and age_min <= 60

    police = sum(1 for o in recent if o.police_action)
    victims = sum(o.victims_count for o in recent)
    deaths = sum(o.deaths_count for o in recent)

    if count >= 5 or (count >= 2 and fresh):
        evidence = "alta evidencia"
    elif count >= 2 or (age_min is not None and age_min <= 180):
        evidence = "evidencia moderada"
    else:
        evidence = "baixa evidencia"

    if count >= 5 and fresh:
        confidence = "alta"
    elif count >= 2:
        confidence = "media"
    else:
        confidence = "baixa"

    parts = [f"{count} registro(s) recente(s)"]
    if age_min is not None:
        parts.append(f"mais recente ha ~{int(age_min)} min")
    if police:
        parts.append(f"{police} com acao policial")
    if victims:
        victim_part = f"{victims} vitima(s)"
        if deaths:
            victim_part += f", {deaths} obito(s)"
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
    """Enriquecimento territorial (IBGE), isolado e tolerante a falha.

    Falha ou ausencia da fonte vira campo nulo + limitacao; nunca quebra a tool.
    E descritivo: nao altera evidencia nem confianca.
    """
    if territory is None:
        return None
    try:
        municipios = await territory.get_municipios()
    except Exception:  # noqa: BLE001 - normalizacao e opcional; degrada sem quebrar
        limitations.append(
            "Normalizacao territorial (IBGE) indisponivel; codigo oficial nao resolvido."
        )
        return None

    context = resolve_territory(municipios, name, uf=uf)
    if context is None:
        limitations.append(
            "Nao foi possivel resolver o codigo IBGE oficial para a cidade consultada."
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
    if context.match_quality == "ambiguo":
        limitations.append(
            "Normalizacao territorial ambigua; verifique a UF do municipio resolvido."
        )
    return context


async def get_recent_activity(
    client: FogoCruzadoClient,
    *,
    city: str,
    region: str | None = None,
    time_window: str = "1h",
    territory: IbgeLocalidadesClient | None = None,
) -> RecentActivityResult:
    query_time = datetime.now(timezone.utc)
    window, window_label, ok = _parse_window(time_window)
    limitations: list[str] = []
    if not ok:
        limitations.append(
            f"time_window '{time_window}' invalido; usando 1h. Use formatos como 30m, 1h, 24h."
        )
    if window > MAX_WINDOW:
        window, window_label = MAX_WINDOW, "7d"
        limitations.append("Janela limitada a 7d nesta versao.")
    cutoff = query_time - window

    sources = [
        SourceRef(
            name="Fogo Cruzado",
            access_type="API REST (JWT)",
            queried_at=query_time,
            url=FONTE_URL,
        )
    ]

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
            activity_summary=f"Cidade '{city}' nao encontrada no catalogo do Fogo Cruzado.",
            evidence_level="sem evidencia",
            confidence_level="baixa",
            limitations=limitations
            + ["Cidade nao encontrada; verifique o nome ou a cobertura da fonte."],
            sources=sources,
        )

    if len(matches) > 1:
        candidates = sorted(
            {f"{c.get('name')} ({_label(c.get('state'))})" for c in matches}
        )[:5]
        limitations.append(
            "Mais de uma cidade corresponde a '"
            f"{city}'. Usando a primeira; especifique a regiao/UF. "
            f"Candidatas: {', '.join(candidates)}."
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
                f"Nenhum registro recente na regiao '{region}' dentro da janela."
            )

    if page_meta.get("hasNextPage"):
        limitations.append(
            f"Mais de {MAX_FETCH} ocorrencias no periodo; mostrando as mais recentes."
        )

    evidence, confidence, summary = _assess(recent, query_time)

    newest_age = None
    ages = [o.occurred_at for o in recent if o.occurred_at]
    if ages:
        newest_age = round((query_time - max(ages)).total_seconds() / 60.0, 1)

    limitations.append(
        "Niveis de evidencia/confianca sao heuristicos preliminares; nao "
        "representam probabilidade calibrada."
    )
    limitations.append(
        "A fonte cobre tiroteios/disparos reportados; operacoes sem registro "
        "podem nao aparecer."
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
        recent_occurrences=recent,
        limitations=limitations,
        sources=sources,
    )
