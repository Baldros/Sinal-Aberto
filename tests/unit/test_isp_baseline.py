"""Tests for the ISP baseline ingestion transforms (pure, no network)."""

from sinal_aberto.ingest.build_isp_baseline import _distribute, _resolve_codes
from sinal_aberto.ingest.isp_transform import (
    aggregate_municipality_month,
    latest_ordinal,
    month_ordinal,
    parse_isp_csv,
    percentile_ranks,
    period_label,
    relative_level,
    window_average,
)

_CSV = (
    "cisp;mes;ano;munic;hom_por_interv_policial;letalidade_violenta\n"
    "1;3;2026;Rio de Janeiro;2;10\n"
    "2;3;2026;Rio de Janeiro;1;5\n"
    "5;2;2026;Niteroi;0;3\n"
    "9;0;2026;Bad Row;9;9\n"  # invalid month -> skipped
)


# -- parse / aggregate -------------------------------------------------


def test_parse_and_aggregate_sums_across_precincts() -> None:
    rows = parse_isp_csv(_CSV)
    assert len(rows) == 3  # the invalid-month row is skipped
    agg = aggregate_municipality_month(rows)
    march = month_ordinal(2026, 3)
    assert agg["Rio de Janeiro"][march] == (3, 15)  # 2+1 police, 10+5 violent
    assert latest_ordinal(agg) == march


def test_parse_raises_on_missing_columns() -> None:
    import pytest

    with pytest.raises(ValueError):
        parse_isp_csv("a;b;c\n1;2;3\n")


# -- window_average ----------------------------------------------------


def test_window_average_divides_by_fixed_window_length() -> None:
    march = month_ordinal(2026, 3)
    series = {march: (3, 15)}  # one month only
    assert window_average(series, march, 12, 0) == 0.25  # 3 / 12
    assert window_average(series, march, 12, 1) == 1.25  # 15 / 12
    assert window_average(series, march, 6, 0) == 0.5  # 3 / 6
    # months outside the window are excluded
    series_old = {month_ordinal(2024, 1): (12, 12), march: (3, 15)}
    assert window_average(series_old, march, 6, 0) == 0.5


# -- relative_level ----------------------------------------------------


def test_relative_level_bands() -> None:
    assert relative_level(0, 0) == "typical"
    assert relative_level(5, 0) == "well above"
    assert relative_level(0.5, 1.0) == "below"
    assert relative_level(1.0, 1.0) == "typical"
    assert relative_level(1.5, 1.0) == "above"
    assert relative_level(3.0, 1.0) == "well above"


# -- percentile_ranks --------------------------------------------------


def test_percentile_ranks_highest_is_one() -> None:
    ranks = percentile_ranks({1: 10.0, 2: 20.0, 3: 20.0})
    assert ranks[1] == round(1 / 3, 4)
    assert ranks[2] == 1.0
    assert ranks[3] == 1.0


def test_period_label() -> None:
    assert period_label(month_ordinal(2026, 5)) == "2026-05"


# -- _resolve_codes / _distribute --------------------------------------


_NAME_TO_CODE = {
    "rio de janeiro": 3304557,
    "cabo frio": 3300704,
    "arraial do cabo": 3300258,
}


def test_resolve_codes_splits_joined_names() -> None:
    assert _resolve_codes("Cabo Frio;Arraial do Cabo", _NAME_TO_CODE) == [3300704, 3300258]
    assert _resolve_codes("Atlantis", _NAME_TO_CODE) == []


def test_distribute_splits_shared_precinct_by_population() -> None:
    march = month_ordinal(2026, 3)
    aggregated = {"Cabo Frio;Arraial do Cabo": {march: (10, 20)}}
    population = {3300704: 230_000, 3300258: 30_000}  # ~88% / ~12%
    by_code, unmapped = _distribute(aggregated, _NAME_TO_CODE, population)

    assert unmapped == []
    total = 230_000 + 30_000
    assert round(by_code[3300704][march][0], 4) == round(10 * 230_000 / total, 4)
    assert round(by_code[3300258][march][0], 4) == round(10 * 30_000 / total, 4)
    # the two shares add back up to the original count
    assert round(by_code[3300704][march][0] + by_code[3300258][march][0], 6) == 10.0


def test_distribute_reports_unmapped() -> None:
    by_code, unmapped = _distribute({"Atlantis": {0: (1, 1)}}, _NAME_TO_CODE, {})
    assert by_code == {}
    assert unmapped == ["Atlantis"]
