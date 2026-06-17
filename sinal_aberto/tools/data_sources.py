"""Ferramenta `list_data_sources`.

Lista as fontes do Sinal Aberto e seu estado. O Fogo Cruzado (unica fonte
integrada) recebe uma sondagem de saude ao vivo; as demais sao listadas como
validadas e ainda nao integradas, refletindo docs/validacao-fontes-secundarias.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..adapters.fogocruzado import FogoCruzadoClient
from ..adapters.ibge import IbgeLocalidadesClient
from ..models import DataSourcesResult, DataSourceStatus

# Catalogo estatico das fontes auxiliares validadas mas ainda nao integradas.
# O IBGE Localidades saiu desta lista: foi promovido a fonte integrada (Tier 1).
_SECONDARY: tuple[dict, ...] = (
    {
        "name": "IBGE Malhas",
        "role": "geometrias oficiais",
        "access_type": "API REST GeoJSON",
        "coverage": "Brasil",
        "known_limitations": [
            "HEAD responde 405; usar GET.",
            "Validada; ainda nao usada nas respostas.",
        ],
    },
    {
        "name": "ISP Dados RJ",
        "role": "historico oficial de seguranca (RJ)",
        "access_type": "CKAN + download CSV/SHP/KML",
        "coverage": "Estado do Rio de Janeiro",
        "known_limitations": [
            "Dado historico/agregado, nao tempo real.",
            "Validada; ainda nao usada nas respostas.",
        ],
    },
    {
        "name": "SINESP/MJSP",
        "role": "historico nacional agregado",
        "access_type": "CKAN + download ZIP/XLSX",
        "coverage": "Brasil",
        "known_limitations": [
            "Agregado; nao serve para eventos em andamento.",
            "Validada; ainda nao usada nas respostas.",
        ],
    },
    {
        "name": "DATA.RIO (ArcGIS)",
        "role": "camadas urbanas do municipio do Rio",
        "access_type": "ArcGIS REST/FeatureServer",
        "coverage": "Municipio do Rio de Janeiro",
        "known_limitations": [
            "Erro logico vem com HTTP 200 + chave 'error'.",
            "Validada; ainda nao usada nas respostas.",
        ],
    },
    {
        "name": "GTFS Rio",
        "role": "mobilidade (linhas e paradas de onibus/BRT)",
        "access_type": "Download ZIP (GTFS estatico)",
        "coverage": "Municipio do Rio de Janeiro",
        "known_limitations": [
            "GTFS estatico, nao tempo real.",
            "Validada; ainda nao usada nas respostas.",
        ],
    },
    {
        "name": "GPS SPPO",
        "role": "contexto operacional de mobilidade",
        "access_type": "REST com janela temporal",
        "coverage": "Municipio do Rio de Janeiro",
        "known_limitations": [
            "Content-Type text/html com corpo JSON.",
            "Exige janela temporal curta.",
            "Validada; ainda nao usada nas respostas.",
        ],
    },
    {
        "name": "COR.Rio",
        "role": "contexto oficial (baixo peso)",
        "access_type": "WordPress REST / RSS",
        "coverage": "Municipio do Rio de Janeiro",
        "known_limitations": [
            "Requer headers de navegador; WAF responde 403 sem eles.",
            "Validada; ainda nao usada nas respostas.",
        ],
    },
)


async def list_data_sources(
    client: FogoCruzadoClient,
    territory: IbgeLocalidadesClient | None = None,
) -> DataSourcesResult:
    query_time = datetime.now(timezone.utc)
    limitations = [
        "Integradas as respostas: Fogo Cruzado (ocorrencias) e IBGE Localidades "
        "(normalizacao territorial). As demais fontes estao validadas mas ainda "
        "nao sao consultadas em tempo real."
    ]

    try:
        last_update = await client.probe()
        fogo_status = "operacional"
    except Exception:  # noqa: BLE001 - qualquer falha vira status indisponivel
        last_update = None
        fogo_status = "indisponivel"
        limitations.append(
            "Fogo Cruzado nao respondeu a sondagem de saude no momento da consulta."
        )

    sources = [
        DataSourceStatus(
            name="Fogo Cruzado",
            role="fonte principal de ocorrencias armadas recentes",
            access_type="API REST (JWT)",
            status=fogo_status,
            coverage="Regioes metropolitanas de Rio de Janeiro, Recife, Bahia e Para",
            last_query_time=query_time,
            last_update_time=last_update,
            known_limitations=[
                "Cobre tiroteios/disparos reportados; nao e radar completo de operacoes.",
                "Operacoes sem disparos ou sem registro podem nao aparecer.",
            ],
        )
    ]

    ibge_status = "integrada"
    if territory is not None:
        try:
            await territory.probe()
            ibge_status = "operacional"
        except Exception:  # noqa: BLE001 - qualquer falha vira status indisponivel
            ibge_status = "indisponivel"
            limitations.append(
                "IBGE Localidades nao respondeu a sondagem de saude no momento da consulta."
            )
    sources.append(
        DataSourceStatus(
            name="IBGE Localidades",
            role="normalizacao territorial oficial (Tier 1)",
            access_type="API REST JSON",
            status=ibge_status,
            coverage="Brasil",
            last_query_time=query_time,
            known_limitations=[
                "Enriquecimento descritivo: resolve codigo IBGE/UF/macrorregiao, "
                "nao altera evidencia nem confianca.",
            ],
        )
    )

    for source in _SECONDARY:
        sources.append(DataSourceStatus(status="validada, nao integrada", **source))

    return DataSourcesResult(
        sources=sources, query_time=query_time, limitations=limitations
    )
