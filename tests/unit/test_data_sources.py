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


async def test_lista_fontes_integradas_operacionais() -> None:
    result = await list_data_sources(_ProbeOK(), territory=_ProbeOK())

    fogo = result.sources[0]
    assert fogo.name == "Fogo Cruzado"
    assert fogo.status == "operacional"
    assert fogo.last_update_time == datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)

    ibge = result.sources[1]
    assert ibge.name == "IBGE Localidades"
    assert ibge.status == "operacional"

    # 2 integradas (Fogo Cruzado + IBGE) + 7 auxiliares
    assert len(result.sources) == 9
    assert all(s.status == "validada, nao integrada" for s in result.sources[2:])


async def test_marca_indisponivel_quando_probe_falha() -> None:
    result = await list_data_sources(_ProbeFail())

    fogo = result.sources[0]
    assert fogo.status == "indisponivel"
    assert fogo.last_update_time is None
    assert any("sondagem de saude" in limit for limit in result.limitations)


async def test_ibge_indisponivel_quando_probe_falha() -> None:
    result = await list_data_sources(_ProbeOK(), territory=_ProbeFail())

    ibge = next(s for s in result.sources if s.name == "IBGE Localidades")
    assert ibge.status == "indisponivel"
    assert any("IBGE Localidades nao respondeu" in limit for limit in result.limitations)


async def test_cor_rio_carrega_limitacao_de_headers() -> None:
    result = await list_data_sources(_ProbeOK(), territory=_ProbeOK())
    cor = next(s for s in result.sources if s.name == "COR.Rio")
    assert any("headers de navegador" in limit for limit in cor.known_limitations)
