"""Recent-intensity profile from Fogo Cruzado occurrences (Tier 2a).

Pure, offline functions. They read raw occurrence dicts (for coordinates and
police units, which never reach the public response) plus the normalized
occurrences, and produce an OperationProfile. Spatial reasoning is plain math
(Haversine), no geospatial service, and the output stays coarse: a concentration
level and a rounded spread, never raw coordinates.
"""

from __future__ import annotations

import math
from typing import Any

from ..models import OperationProfile, RecentOccurrence

_EARTH_RADIUS_M = 6_371_000.0
# Spread thresholds (diameter of the point set), in meters.
_CONCENTRATED_MAX_M = 500.0
_LOCALIZED_MAX_M = 2_000.0


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def parse_coord(raw: dict[str, Any]) -> tuple[float, float] | None:
    """Latitude/longitude as a float pair, or None when missing/invalid."""
    lat = _to_float(raw.get("latitude"))
    lon = _to_float(raw.get("longitude"))
    if lat is None or lon is None:
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    if lat == 0.0 and lon == 0.0:  # null island = missing geocode
        return None
    return (lat, lon)


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between two lat/long points, in meters."""
    lat1, lon1 = a
    lat2, lon2 = b
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def max_spread_m(points: list[tuple[float, float] | None]) -> float | None:
    """Largest pairwise distance (the set's diameter); None if fewer than 2 points."""
    pts = [p for p in points if p is not None]
    if len(pts) < 2:
        return None
    return max(
        haversine_m(pts[i], pts[j])
        for i in range(len(pts))
        for j in range(i + 1, len(pts))
    )


def classify_concentration(
    points: list[tuple[float, float] | None],
) -> tuple[str, int | None]:
    """Coarse concentration level and rounded spread from a set of points."""
    spread = max_spread_m(points)
    if spread is None:
        return "indeterminate", None
    approx = int(round(spread / 100.0) * 100)
    if spread <= _CONCENTRATED_MAX_M:
        level = "concentrated"
    elif spread <= _LOCALIZED_MAX_M:
        level = "localized"
    else:
        level = "dispersed"
    return level, approx


def _unit_names(unit: Any) -> list[str]:
    if isinstance(unit, dict):
        name = unit.get("name")
        return [name.strip()] if name and name.strip() else []
    if isinstance(unit, str):
        return [unit.strip()] if unit.strip() else []
    if isinstance(unit, list):
        names: list[str] = []
        for item in unit:
            names.extend(_unit_names(item))
        return names
    return []


def distinct_police_units(raw_occurrences: list[dict[str, Any]]) -> int:
    """Count distinct police units across the window (operation breadth)."""
    names: set[str] = set()
    for raw in raw_occurrences:
        unit = (raw.get("contextInfo") or {}).get("policeUnit")
        names.update(_unit_names(unit))
    return len(names)


def recency_signal(newest_age_minutes: float | None) -> str:
    """Map the age of the most recent occurrence to a decay band."""
    if newest_age_minutes is None:
        return "recent"
    if newest_age_minutes <= 30:
        return "very recent"
    if newest_age_minutes <= 90:
        return "recent"
    if newest_age_minutes <= 180:
        return "cooling"
    return "likely subsided"


def _build_note(
    count: int,
    massacre: bool,
    units: int,
    concentration: str,
    spread: int | None,
    recency: str,
) -> str:
    parts = [f"{count} occurrence(s)"]
    if massacre:
        parts.append("massacre flagged")
    if units:
        parts.append(f"{units} distinct police unit(s)")
    if concentration == "indeterminate":
        parts.append("spatial spread indeterminate")
    else:
        spread_txt = f" (~{spread} m spread)" if spread is not None else ""
        parts.append(f"{concentration}{spread_txt}")
    parts.append(f"activity {recency}")
    note = "; ".join(parts) + "."
    if concentration == "concentrated":
        note += " A tight cluster may partly reflect source coordinate approximation."
    return note


def build_operation_profile(
    raw_occurrences: list[dict[str, Any]],
    occurrences: list[RecentOccurrence],
    newest_age_minutes: float | None,
) -> OperationProfile | None:
    """Assemble the recent-intensity profile, or None when there is nothing to profile."""
    if not occurrences:
        return None
    massacre_flagged = any(o.massacre for o in occurrences)
    units = distinct_police_units(raw_occurrences)
    concentration, spread = classify_concentration([parse_coord(r) for r in raw_occurrences])
    recency = recency_signal(newest_age_minutes)
    note = _build_note(len(occurrences), massacre_flagged, units, concentration, spread, recency)
    return OperationProfile(
        massacre_flagged=massacre_flagged,
        distinct_police_units=units,
        spatial_concentration=concentration,
        approx_spread_m=spread,
        recency_signal=recency,
        note=note,
    )
