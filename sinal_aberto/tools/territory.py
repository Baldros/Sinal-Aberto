"""Resolucao territorial: casa a cidade pedida com o municipio oficial do IBGE.

Funcoes puras, sem rede: recebem o catalogo de municipios (entregue pelo
`IbgeLocalidadesClient`) e devolvem um `TerritorialContext`. A normalizacao por
slug (sem acento, sem caixa) torna o casamento robusto a "Sao Goncalo" vs
"Sao Goncalo" e desambigua por UF quando o nome se repete entre estados.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from ..models import TerritorialContext


def slugify(text: str | None) -> str:
    """Normaliza para comparacao: sem acento, minusculo, espacos colapsados."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(ascii_text.casefold().split())


def _uf_node(municipio: dict[str, Any]) -> dict[str, Any]:
    return (
        ((municipio.get("microrregiao") or {}).get("mesorregiao") or {}).get("UF")
        or {}
    )


def _uf_sigla(municipio: dict[str, Any]) -> str | None:
    return _uf_node(municipio).get("sigla")


def _uf_nome(municipio: dict[str, Any]) -> str | None:
    return _uf_node(municipio).get("nome")


def _macro_region(municipio: dict[str, Any]) -> str | None:
    return (_uf_node(municipio).get("regiao") or {}).get("nome")


def _matches_uf(municipio: dict[str, Any], uf_slug: str) -> bool:
    """Compara a UF pedida contra a sigla OU o nome (o Fogo Cruzado manda o nome)."""
    return uf_slug in (slugify(_uf_sigla(municipio)), slugify(_uf_nome(municipio)))


def _to_context(municipio: dict[str, Any], match_quality: str) -> TerritorialContext:
    code = municipio.get("id")
    return TerritorialContext(
        ibge_city_code=int(code) if isinstance(code, int) or str(code).isdigit() else None,
        resolved_name=municipio.get("nome"),
        uf=_uf_sigla(municipio),
        macro_region=_macro_region(municipio),
        match_quality=match_quality,
    )


def resolve_territory(
    municipios: list[dict[str, Any]],
    name: str,
    uf: str | None = None,
) -> TerritorialContext | None:
    """Resolve a cidade no catalogo do IBGE.

    Estrategia: casamento exato por slug; se houver UF (sigla ou nome), usa-a para
    desambiguar. Sem casamento exato, tenta prefixo/substring ("aproximado"). Sem
    nenhum, devolve None. Multiplos exatos que a UF nao resolve viram "ambiguo".
    """
    target = slugify(name)
    if not target:
        return None
    uf_slug = slugify(uf)

    exact = [m for m in municipios if slugify(m.get("nome")) == target]
    if uf_slug:
        narrowed = [m for m in exact if _matches_uf(m, uf_slug)]
        if narrowed:
            exact = narrowed
    if len(exact) == 1:
        return _to_context(exact[0], "exato")
    if len(exact) > 1:
        return _to_context(exact[0], "ambiguo")

    approx = [m for m in municipios if target in slugify(m.get("nome"))]
    if uf_slug:
        narrowed = [m for m in approx if _matches_uf(m, uf_slug)]
        if narrowed:
            approx = narrowed
    if len(approx) >= 1:
        quality = "aproximado" if len(approx) == 1 else "ambiguo"
        return _to_context(approx[0], quality)

    return None
