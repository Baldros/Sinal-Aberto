"""Testes da resolucao territorial (IBGE), funcoes puras, sem rede."""

from typing import Any

from sinal_aberto.models import TerritorialContext
from sinal_aberto.tools.territory import resolve_territory, slugify


def _muni(
    code: int,
    nome: str,
    sigla: str,
    uf_nome: str,
    regiao: str = "Sudeste",
) -> dict[str, Any]:
    """Monta um municipio no formato do IBGE Localidades."""
    return {
        "id": code,
        "nome": nome,
        "microrregiao": {
            "mesorregiao": {
                "UF": {
                    "sigla": sigla,
                    "nome": uf_nome,
                    "regiao": {"nome": regiao},
                }
            }
        },
    }


CATALOGO = [
    _muni(3304557, "Rio de Janeiro", "RJ", "Rio de Janeiro"),
    _muni(3304904, "São Gonçalo", "RJ", "Rio de Janeiro"),
    _muni(2412405, "São Gonçalo do Amarante", "RN", "Nordeste"),
    # Mesmo nome em UFs diferentes: caso de ambiguidade.
    _muni(3550308, "Bom Jesus", "SP", "São Paulo"),
    _muni(4302808, "Bom Jesus", "RS", "Sul"),
]


# -- slugify -----------------------------------------------------------


def test_slugify_remove_acento_e_caixa() -> None:
    assert slugify("São Gonçalo") == "sao goncalo"
    assert slugify("  RIO   de Janeiro ") == "rio de janeiro"
    assert slugify(None) == ""
    assert slugify("") == ""


# -- resolve_territory: casamento exato --------------------------------


def test_resolve_exato_devolve_contexto_completo() -> None:
    ctx = resolve_territory(CATALOGO, "Rio de Janeiro")
    assert isinstance(ctx, TerritorialContext)
    assert ctx.ibge_city_code == 3304557
    assert ctx.resolved_name == "Rio de Janeiro"
    assert ctx.uf == "RJ"
    assert ctx.macro_region == "Sudeste"
    assert ctx.match_quality == "exato"


def test_resolve_ignora_acento() -> None:
    ctx = resolve_territory(CATALOGO, "sao goncalo")
    assert ctx is not None
    assert ctx.ibge_city_code == 3304904
    assert ctx.match_quality == "exato"


def test_resolve_desambigua_por_uf_sigla() -> None:
    ctx = resolve_territory(CATALOGO, "Bom Jesus", uf="RS")
    assert ctx is not None
    assert ctx.ibge_city_code == 4302808
    assert ctx.match_quality == "exato"


def test_resolve_desambigua_por_uf_nome() -> None:
    # O Fogo Cruzado manda o nome da UF, nao a sigla.
    ctx = resolve_territory(CATALOGO, "Bom Jesus", uf="São Paulo")
    assert ctx is not None
    assert ctx.ibge_city_code == 3550308
    assert ctx.match_quality == "exato"


def test_resolve_ambiguo_sem_uf() -> None:
    ctx = resolve_territory(CATALOGO, "Bom Jesus")
    assert ctx is not None
    assert ctx.match_quality == "ambiguo"


# -- resolve_territory: aproximado e ausencia --------------------------


def test_resolve_aproximado_por_substring() -> None:
    ctx = resolve_territory(CATALOGO, "Amarante")
    assert ctx is not None
    assert ctx.ibge_city_code == 2412405
    assert ctx.match_quality == "aproximado"


def test_resolve_sem_match_devolve_none() -> None:
    assert resolve_territory(CATALOGO, "Atlantida") is None
    assert resolve_territory(CATALOGO, "") is None
