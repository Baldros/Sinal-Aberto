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


def _municipality_code(municipality: dict[str, Any]) -> int | None:
    code = municipality.get("id")
    if isinstance(code, int):
        return code
    if isinstance(code, str) and code.isdigit():
        return int(code)
    return None


def municipality_summary(municipality: dict[str, Any]) -> dict[str, Any]:
    """Compact, agent-friendly view of one IBGE municipality."""
    return {
        "ibge_city_code": _municipality_code(municipality),
        "name": municipality.get("nome"),
        "uf": _uf_abbreviation(municipality),
        "macro_region": _macro_region(municipality),
    }


def _to_context(municipality: dict[str, Any], match_quality: str) -> TerritorialContext:
    summary = municipality_summary(municipality)
    return TerritorialContext(
        ibge_city_code=summary["ibge_city_code"],
        resolved_name=summary["name"],
        uf=summary["uf"],
        macro_region=summary["macro_region"],
        match_quality=match_quality,
    )


def find_candidates(
    municipalities: list[dict[str, Any]],
    name: str,
    uf: str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Find municipalities matching a name, narrowed by state when given.

    Returns (matches, tier) where tier is "exact", "approximate", or "none".
    Exact slug matches win; otherwise substring matches are returned. A state
    (abbreviation or name) narrows either pass only when it leaves something.
    Callers decide how to treat multiple matches.
    """
    target = slugify(name)
    if not target:
        return [], "none"
    uf_slug = slugify(uf)

    exact = [m for m in municipalities if slugify(m.get("nome")) == target]
    if uf_slug:
        narrowed = [m for m in exact if _matches_uf(m, uf_slug)]
        if narrowed:
            exact = narrowed
    if exact:
        return exact, "exact"

    approx = [m for m in municipalities if target in slugify(m.get("nome"))]
    if uf_slug:
        narrowed = [m for m in approx if _matches_uf(m, uf_slug)]
        if narrowed:
            approx = narrowed
    if approx:
        return approx, "approximate"

    return [], "none"


def resolve_territory(
    municipalities: list[dict[str, Any]],
    name: str,
    uf: str | None = None,
) -> TerritorialContext | None:
    """Resolve a city to a single best IBGE municipality.

    Thin wrapper over find_candidates: returns the first match, labelling it
    "ambiguous" when more than one remains, or None when nothing matches.
    """
    matches, tier = find_candidates(municipalities, name, uf)
    if not matches:
        return None
    quality = "ambiguous" if len(matches) > 1 else ("exact" if tier == "exact" else "approximate")
    return _to_context(matches[0], quality)
