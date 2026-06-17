"""Servidor MCP do Sinal Aberto.

Expoe as ferramentas de consulta sobre a stack FastMCP, com transporte Streamable
HTTP. As tools retornam modelos Pydantic, que o FastMCP serializa como conteudo
estruturado JSON.

Execucao local (a partir da raiz do repositorio):

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
        "Ferramentas de consulta a sinais recentes de atividade armada ou policial "
        "no Brasil, com base na API Fogo Cruzado. As respostas sempre trazem fonte, "
        "horario e limitacoes, e expressam evidencia e incerteza em vez de afirmacoes "
        "absolutas. Nao forneca rotas, fuga, aproximacao de agentes nem decisoes taticas."
    ),
)

_client: FogoCruzadoClient | None = None
_ibge_client: IbgeLocalidadesClient | None = None


def _get_client() -> FogoCruzadoClient:
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
    global _ibge_client
    if _ibge_client is None:
        settings = get_settings()
        _ibge_client = IbgeLocalidadesClient(
            base_url=settings.ibge_base_url,
            timeout=settings.http_timeout,
            catalog_ttl=settings.ibge_cache_ttl,
        )
    return _ibge_client


@mcp.tool
async def get_recent_activity(
    city: str,
    region: str | None = None,
    time_window: str = "1h",
) -> RecentActivityResult:
    """Consulta sinais recentes de atividade armada ou policial em uma cidade.

    Args:
        city: nome da cidade (ex.: "Rio de Janeiro", "Recife").
        region: bairro ou regiao opcional para filtrar dentro da cidade.
        time_window: janela temporal recente, ex.: "30m", "1h", "6h", "24h".

    Retorna um resumo rastreavel: contagem de ocorrencias, nivel de evidencia,
    nivel de confianca, ocorrencias normalizadas (por bairro/regiao, sem
    coordenadas exatas), fonte, horario de consulta/atualizacao e limitacoes.
    """
    return await _get_recent_activity(
        _get_client(),
        city=city,
        region=region,
        time_window=time_window,
        territory=_get_ibge_client(),
    )


@mcp.tool
async def list_data_sources() -> DataSourcesResult:
    """Lista as fontes de dados do Sinal Aberto e seu estado operacional.

    O Fogo Cruzado e o IBGE Localidades sao marcados como integrados, com sondagem
    de saude ao vivo; as demais fontes auxiliares aparecem como validadas e ainda
    nao integradas, conforme o estado real do sistema.
    """
    return await _list_data_sources(_get_client(), territory=_get_ibge_client())


def main() -> None:
    settings = get_settings()
    mcp.run(transport="http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
