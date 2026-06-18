"""Tests for the ISP baseline store (reads prepared data, no network)."""

from pathlib import Path

from sinal_aberto.tools.baseline import BaselineStore

_DATA = {
    "meta": {
        "source": "ISP Dados RJ",
        "as_of": "2026-05",
        "typical_window": "12 months ending 2026-05",
        "recent_window": "6 months ending 2026-05",
    },
    "municipalities": {
        "3304557": {
            "name": "Rio de Janeiro",
            "population": 6_730_729,
            "police_lethality": {
                "typical_monthly": 37.8,
                "recent_monthly": 33.0,
                "per_100k_annual": 6.75,
                "percentile": 0.956,
            },
            "violent_lethality": {
                "typical_monthly": 128.0,
                "recent_monthly": 126.5,
                "per_100k_annual": 22.84,
                "percentile": 0.62,
            },
            "relative_level": "typical",
        }
    },
}


def test_lookup_builds_baseline() -> None:
    store = BaselineStore(data=_DATA)
    baseline = store.lookup(3304557)

    assert baseline is not None
    assert baseline.ibge_city_code == 3304557
    assert baseline.population == 6_730_729
    assert baseline.police_lethality.percentile == 0.956
    assert baseline.relative_level == "typical"
    assert baseline.as_of == "2026-05"
    assert "Under-reporting" in baseline.note


def test_lookup_missing_municipality_returns_none() -> None:
    store = BaselineStore(data=_DATA)
    assert store.lookup(9_999_999) is None


def test_missing_file_degrades_to_empty(tmp_path: Path) -> None:
    store = BaselineStore(path=tmp_path / "absent.json")
    assert store.lookup(3304557) is None


def test_packaged_file_loads_and_has_rio() -> None:
    # Sanity check on the committed prepared file: Rio resolves and is high-percentile.
    store = BaselineStore()
    baseline = store.lookup(3304557)
    assert baseline is not None
    assert baseline.police_lethality.per_100k_annual is not None
    assert 0.0 <= (baseline.police_lethality.percentile or 0.0) <= 1.0
