"""Tests for the recent-intensity (operation profile) helpers, no network."""

import pytest

from sinal_aberto.models import OperationProfile, RecentOccurrence
from sinal_aberto.tools.operations import (
    build_operation_profile,
    classify_concentration,
    distinct_police_units,
    haversine_m,
    parse_coord,
    recency_signal,
)


# -- parse_coord -------------------------------------------------------


def test_parse_coord_accepts_floats_and_comma_decimals() -> None:
    assert parse_coord({"latitude": -22.9, "longitude": -43.2}) == (-22.9, -43.2)
    assert parse_coord({"latitude": "-22,9", "longitude": "-43,2"}) == (-22.9, -43.2)


def test_parse_coord_rejects_missing_and_null_island() -> None:
    assert parse_coord({"latitude": None, "longitude": -43.2}) is None
    assert parse_coord({"latitude": 0.0, "longitude": 0.0}) is None
    assert parse_coord({}) is None


# -- haversine ---------------------------------------------------------


def test_haversine_one_degree_longitude_at_equator() -> None:
    # ~111 km per degree of longitude at the equator.
    d = haversine_m((0.0, 0.0), (0.0, 1.0))
    assert 110_000 < d < 112_000


# -- classify_concentration --------------------------------------------


def test_concentration_bands() -> None:
    base = (-22.90, -43.20)
    # ~111 m apart -> concentrated
    level, spread = classify_concentration([base, (-22.901, -43.20)])
    assert level == "concentrated"
    assert spread is not None and spread <= 500
    # ~1.1 km apart -> localized
    level, _ = classify_concentration([base, (-22.91, -43.20)])
    assert level == "localized"
    # ~3.3 km apart -> dispersed
    level, _ = classify_concentration([base, (-22.93, -43.20)])
    assert level == "dispersed"


def test_concentration_indeterminate_with_few_points() -> None:
    assert classify_concentration([(-22.9, -43.2)]) == ("indeterminate", None)
    assert classify_concentration([None, None]) == ("indeterminate", None)


# -- distinct_police_units ---------------------------------------------


def test_distinct_police_units_counts_unique_names() -> None:
    raw = [
        {"contextInfo": {"policeUnit": {"id": "1", "name": "BOPE"}}},
        {"contextInfo": {"policeUnit": {"id": "1", "name": "BOPE"}}},
        {"contextInfo": {"policeUnit": {"id": "2", "name": "UPP"}}},
        {"contextInfo": {"policeUnit": None}},
        {"contextInfo": {}},
    ]
    assert distinct_police_units(raw) == 2


# -- recency_signal ----------------------------------------------------


@pytest.mark.parametrize(
    "age,expected",
    [
        (5, "very recent"),
        (60, "recent"),
        (120, "cooling"),
        (300, "likely subsided"),
        (None, "recent"),
    ],
)
def test_recency_signal_bands(age, expected) -> None:
    assert recency_signal(age) == expected


# -- build_operation_profile -------------------------------------------


def test_build_profile_aggregates_signals() -> None:
    occurrences = [
        RecentOccurrence(neighborhood="Penha", massacre=True),
        RecentOccurrence(neighborhood="Penha"),
    ]
    raw = [
        {"latitude": -22.90, "longitude": -43.20, "contextInfo": {"policeUnit": {"name": "BOPE"}}},
        {"latitude": -22.901, "longitude": -43.20, "contextInfo": {"policeUnit": {"name": "UPP"}}},
    ]
    profile = build_operation_profile(raw, occurrences, newest_age_minutes=10)
    assert isinstance(profile, OperationProfile)
    assert profile.massacre_flagged is True
    assert profile.distinct_police_units == 2
    assert profile.spatial_concentration == "concentrated"
    assert profile.recency_signal == "very recent"
    assert "approximation" in profile.note  # geocoding caveat for tight clusters


def test_build_profile_none_without_occurrences() -> None:
    assert build_operation_profile([], [], newest_age_minutes=None) is None
