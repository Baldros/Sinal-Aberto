"""Tests for territorial resolution (IBGE), pure functions without network calls."""

from typing import Any

from sinal_aberto.models import TerritorialContext
from sinal_aberto.tools.territory import resolve_territory, slugify


def _muni(
    code: int,
    nome: str,
    sigla: str,
    uf_nome: str,
    region: str = "Sudeste",
) -> dict[str, Any]:
    """Build one municipality in the IBGE Localidades response shape."""
    return {
        "id": code,
        "nome": nome,
        "microrregiao": {
            "mesorregiao": {
                "UF": {
                    "sigla": sigla,
                    "nome": uf_nome,
                    "regiao": {"nome": region},
                }
            }
        },
    }


CATALOG = [
    _muni(3304557, "Rio de Janeiro", "RJ", "Rio de Janeiro"),
    _muni(3304904, "S\u00e3o Gon\u00e7alo", "RJ", "Rio de Janeiro"),
    _muni(2412405, "S\u00e3o Gon\u00e7alo do Amarante", "RN", "Nordeste"),
    # Same name in different states: ambiguity case.
    _muni(3550308, "Bom Jesus", "SP", "S\u00e3o Paulo"),
    _muni(4302808, "Bom Jesus", "RS", "Sul"),
]


# -- slugify ------------------------------------------------------------


def test_slugify_removes_accents_and_case() -> None:
    assert slugify("S\u00e3o Gon\u00e7alo") == "sao goncalo"
    assert slugify("  RIO   de Janeiro ") == "rio de janeiro"
    assert slugify(None) == ""
    assert slugify("") == ""


# -- resolve_territory: exact match ------------------------------------


def test_resolve_exact_returns_full_context() -> None:
    ctx = resolve_territory(CATALOG, "Rio de Janeiro")
    assert isinstance(ctx, TerritorialContext)
    assert ctx.ibge_city_code == 3304557
    assert ctx.resolved_name == "Rio de Janeiro"
    assert ctx.uf == "RJ"
    assert ctx.macro_region == "Sudeste"
    assert ctx.match_quality == "exact"


def test_resolve_ignores_accents() -> None:
    ctx = resolve_territory(CATALOG, "sao goncalo")
    assert ctx is not None
    assert ctx.ibge_city_code == 3304904
    assert ctx.match_quality == "exact"


def test_resolve_disambiguates_by_state_abbreviation() -> None:
    ctx = resolve_territory(CATALOG, "Bom Jesus", uf="RS")
    assert ctx is not None
    assert ctx.ibge_city_code == 4302808
    assert ctx.match_quality == "exact"


def test_resolve_disambiguates_by_state_name() -> None:
    # Fogo Cruzado sends the state name, not the abbreviation.
    ctx = resolve_territory(CATALOG, "Bom Jesus", uf="S\u00e3o Paulo")
    assert ctx is not None
    assert ctx.ibge_city_code == 3550308
    assert ctx.match_quality == "exact"


def test_resolve_ambiguous_without_state() -> None:
    ctx = resolve_territory(CATALOG, "Bom Jesus")
    assert ctx is not None
    assert ctx.match_quality == "ambiguous"


# -- resolve_territory: approximate and missing match -------------------


def test_resolve_approximate_by_substring() -> None:
    ctx = resolve_territory(CATALOG, "Amarante")
    assert ctx is not None
    assert ctx.ibge_city_code == 2412405
    assert ctx.match_quality == "approximate"


def test_resolve_without_match_returns_none() -> None:
    assert resolve_territory(CATALOG, "Atlantis") is None
    assert resolve_territory(CATALOG, "") is None
