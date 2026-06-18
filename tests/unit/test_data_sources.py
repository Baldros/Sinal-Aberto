"""Tests for the list_data_sources tool, without network calls."""

from datetime import datetime, timezone

from sinal_aberto.adapters.fogocruzado import FogoCruzadoError
from sinal_aberto.tools.data_sources import list_data_sources


class _ProbeOK:
    async def probe(self):
        return datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)


class _ProbeFail:
    async def probe(self):
        raise FogoCruzadoError("unavailable")


async def test_lists_integrated_operational_sources() -> None:
    result = await list_data_sources(
        _ProbeOK(), territory=_ProbeOK(), corroboration=_ProbeOK()
    )

    fogo = result.sources[0]
    assert fogo.name == "Fogo Cruzado"
    assert fogo.status == "operational"
    assert fogo.last_update_time == datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)

    ibge = result.sources[1]
    assert ibge.name == "IBGE Localidades"
    assert ibge.status == "operational"

    cor = result.sources[2]
    assert cor.name == "COR.Rio"
    assert cor.status == "operational"

    # 3 integrated sources (Fogo Cruzado + IBGE + COR.Rio) plus 6 auxiliary sources.
    assert len(result.sources) == 9
    assert all(s.status == "validated, not integrated" for s in result.sources[3:])


async def test_marks_unavailable_when_probe_fails() -> None:
    result = await list_data_sources(_ProbeFail())

    fogo = result.sources[0]
    assert fogo.status == "unavailable"
    assert fogo.last_update_time is None
    assert any("health probe" in limit for limit in result.limitations)


async def test_marks_ibge_unavailable_when_probe_fails() -> None:
    result = await list_data_sources(_ProbeOK(), territory=_ProbeFail())

    ibge = next(s for s in result.sources if s.name == "IBGE Localidades")
    assert ibge.status == "unavailable"
    assert any("IBGE Localidades did not respond" in limit for limit in result.limitations)


async def test_cor_rio_loads_header_limitation() -> None:
    result = await list_data_sources(_ProbeOK(), territory=_ProbeOK(), corroboration=_ProbeOK())
    cor = next(s for s in result.sources if s.name == "COR.Rio")
    assert any("browser-like headers" in limit for limit in cor.known_limitations)


async def test_marks_cor_rio_unavailable_when_probe_fails() -> None:
    result = await list_data_sources(_ProbeOK(), territory=_ProbeOK(), corroboration=_ProbeFail())

    cor = next(s for s in result.sources if s.name == "COR.Rio")
    assert cor.status == "unavailable"
    assert any("COR.Rio did not respond" in limit for limit in result.limitations)
