"""Territory resolution: match the requested city to the official IBGE city.

These are pure, offline functions: they receive the municipality catalog from
`IbgeLocalidadesClient` and return a `TerritorialContext`. Slug normalization
removes accents and case differences, making matches robust to accented and
unaccented user input and allowing state-based disambiguation when city names
repeat across states.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from ..models import TerritorialContext


def slugify(text: str | None) -> str:
    """Normalize text for comparison: ASCII accents stripped, lowercase, compact spaces."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(ascii_text.casefold().split())


def _uf_node(municipality: dict[str, Any]) -> dict[str, Any]:
    return (
        ((municipality.get("microrregiao") or {}).get("mesorregiao") or {}).get("UF")
        or {}
    )


def _uf_abbreviation(municipality: dict[str, Any]) -> str | None:
    return _uf_node(municipality).get("sigla")


def _uf_name(municipality: dict[str, Any]) -> str | None:
    return _uf_node(municipality).get("nome")


def _macro_region(municipality: dict[str, Any]) -> str | None:
    return (_uf_node(municipality).get("regiao") or {}).get("nome")


def _matches_uf(municipality: dict[str, Any], uf_slug: str) -> bool:
    """Compare the requested state against either abbreviation or name."""
    return uf_slug in (
        slugify(_uf_abbreviation(municipality)),
        slugify(_uf_name(municipality)),
    )


def _to_context(municipality: dict[str, Any], match_quality: str) -> TerritorialContext:
    code = municipality.get("id")
    return TerritorialContext(
        ibge_city_code=int(code) if isinstance(code, int) or str(code).isdigit() else None,
        resolved_name=municipality.get("nome"),
        uf=_uf_abbreviation(municipality),
        macro_region=_macro_region(municipality),
        match_quality=match_quality,
    )


def resolve_territory(
    municipalities: list[dict[str, Any]],
    name: str,
    uf: str | None = None,
) -> TerritorialContext | None:
    """Resolve a city inside the IBGE municipality catalog.

    Strategy: exact slug match first; if a state abbreviation or name is
    available, use it to disambiguate. Without an exact match, fall back to a
    substring match. Multiple unresolved matches are reported as ambiguous.
    """
    target = slugify(name)
    if not target:
        return None
    uf_slug = slugify(uf)

    exact = [m for m in municipalities if slugify(m.get("nome")) == target]
    if uf_slug:
        narrowed = [m for m in exact if _matches_uf(m, uf_slug)]
        if narrowed:
            exact = narrowed
    if len(exact) == 1:
        return _to_context(exact[0], "exact")
    if len(exact) > 1:
        return _to_context(exact[0], "ambiguous")

    approx = [m for m in municipalities if target in slugify(m.get("nome"))]
    if uf_slug:
        narrowed = [m for m in approx if _matches_uf(m, uf_slug)]
        if narrowed:
            approx = narrowed
    if len(approx) >= 1:
        quality = "approximate" if len(approx) == 1 else "ambiguous"
        return _to_context(approx[0], quality)

    return None
