"""Testes da ferramenta list_data_sources, sem rede."""

from datetime import datetime, timezone

from sinal_aberto.adapters.fogocruzado import FogoCruzadoError
from sinal_aberto.tools.data_sources import list_data_sources


class _ProbeOK:
    async def probe(self):
        return datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)


class _ProbeFail:
    async def probe(self):
        raise FogoCruzadoError("indisponivel")


async def test_lista_fonte_principal_operacional() -> None:
    result = await list_data_sources(_ProbeOK())

    fogo = result.sources[0]
    assert fogo.name == "Fogo Cruzado"
    assert fogo.status == "operacional"
    assert fogo.last_update_time == datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
    # 1 principal + 8 auxiliares
    assert len(result.sources) == 9
    assert all(s.status == "validada, nao integrada" for s in result.sources[1:])


async def test_marca_indisponivel_quando_probe_falha() -> None:
    result = await list_data_sources(_ProbeFail())

    fogo = result.sources[0]
    assert fogo.status == "indisponivel"
    assert fogo.last_update_time is None
    assert any("sondagem de saude" in limit for limit in result.limitations)


async def test_cor_rio_carrega_limitacao_de_headers() -> None:
    result = await list_data_sources(_ProbeOK())
    cor = next(s for s in result.sources if s.name == "COR.Rio")
    assert any("headers de navegador" in limit for limit in cor.known_limitations)
