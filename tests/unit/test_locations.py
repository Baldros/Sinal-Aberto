"""Tests for the resolve_location tool, without network calls."""

from typing import Any

from sinal_aberto.tools.locations import resolve_location


def _muni(code: int, nome: str, sigla: str, uf_nome: str, regiao: str = "Sudeste") -> dict[str, Any]:
    return {
        "id": code,
        "nome": nome,
        "microrregiao": {
            "mesorregiao": {
                "UF": {"sigla": sigla, "nome": uf_nome, "regiao": {"nome": regiao}}
            }
        },
    }


CATALOG = [
    _muni(3304557, "Rio de Janeiro", "RJ", "Rio de Janeiro"),
    _muni(3550308, "Bom Jesus", "SP", "São Paulo"),
    _muni(4302808, "Bom Jesus", "RS", "Sul"),
    _muni(2412405, "São Gonçalo do Amarante", "RN", "Nordeste"),
]


class FakeTerritory:
    def __init__(self, municipalities=None, *, fail: bool = False) -> None:
        self._municipalities = municipalities if municipalities is not None else CATALOG
        self._fail = fail

    async def get_municipalities(self):
        if self._fail:
            raise RuntimeError("ibge down")
        return self._municipalities


async def test_resolved_single_exact_match() -> None:
    result = await resolve_location(FakeTerritory(), name="Rio de Janeiro")
    assert result.status == "resolved"
    assert len(result.candidates) == 1
    assert result.candidates[0].ibge_city_code == 3304557
    assert any(s.name == "IBGE Localidades" for s in result.sources)


async def test_ambiguous_lists_all_candidates() -> None:
    result = await resolve_location(FakeTerritory(), name="Bom Jesus")
    assert result.status == "ambiguous"
    codes = {c.ibge_city_code for c in result.candidates}
    assert codes == {3550308, 4302808}
    assert any("disambiguate" in limit for limit in result.limitations)


async def test_uf_disambiguates_to_resolved() -> None:
    result = await resolve_location(FakeTerritory(), name="Bom Jesus", uf="RS")
    assert result.status == "resolved"
    assert len(result.candidates) == 1
    assert result.candidates[0].ibge_city_code == 4302808
    assert result.uf_filter == "RS"


async def test_approximate_substring_match() -> None:
    result = await resolve_location(FakeTerritory(), name="Amarante")
    assert result.status == "approximate"
    assert result.candidates[0].ibge_city_code == 2412405
    assert any("partial" in limit for limit in result.limitations)


async def test_not_found() -> None:
    result = await resolve_location(FakeTerritory(), name="Atlantida")
    assert result.status == "not_found"
    assert result.candidates == []


async def test_unavailable_source_degrades_gracefully() -> None:
    result = await resolve_location(FakeTerritory(fail=True), name="Rio de Janeiro")
    assert result.status == "not_found"
    assert result.candidates == []
    assert any("unavailable" in limit for limit in result.limitations)
    assert result.sources == []
