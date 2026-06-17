"""Tests for the get_recent_activity tool and its helpers, without network calls."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from sinal_aberto.models import RecentOccurrence
from sinal_aberto.tools import recent_activity as ra


# -- fixture helpers ----------------------------------------------------


class FakeClient:
    """Stand-in for FogoCruzadoClient: returns canned data and records calls."""

    def __init__(
        self,
        cities: list[dict[str, Any]],
        occurrences: list[dict[str, Any]],
        page_meta: dict[str, Any] | None = None,
        last_update: datetime | None = None,
    ) -> None:
        self._cities = cities
        self._occurrences = occurrences
        self._page_meta = page_meta or {}
        self._last_update = last_update
        self.occurrence_calls: list[dict[str, Any]] = []

    async def get_cities(self) -> list[dict[str, Any]]:
        return self._cities

    async def get_occurrences(self, params):
        self.occurrence_calls.append(params)
        return self._occurrences, self._page_meta, self._last_update


def _city(name: str = "Rio de Janeiro", city_id: str = "c1", state: str = "Rio de Janeiro"):
    return {"id": city_id, "name": name, "state": {"id": f"s-{state}", "name": state}}


def _occ(minutes_ago: int, **overrides: Any) -> dict[str, Any]:
    occurred = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    base: dict[str, Any] = {
        "date": occurred.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state": {"id": "s", "name": "Rio de Janeiro"},
        "city": {"id": "c1", "name": "Rio de Janeiro"},
        "neighborhood": {"id": "n", "name": "Penha"},
        "subNeighborhood": None,
        "locality": {"id": "l", "name": "Morro da Fe"},
        "policeAction": False,
        "agentPresence": False,
        "contextInfo": {"mainReason": {"id": "r", "name": "Police operation"}},
        "transports": [],
        "victims": [],
        "animalVictims": [],
    }
    base.update(overrides)
    return base


# -- _parse_window ------------------------------------------------------


@pytest.mark.parametrize(
    "value,delta,label",
    [
        ("30m", timedelta(minutes=30), "30m"),
        ("1h", timedelta(hours=1), "1h"),
        ("24h", timedelta(hours=24), "24h"),
        ("2d", timedelta(days=2), "2d"),
    ],
)
def test_parse_window_valid(value: str, delta: timedelta, label: str) -> None:
    parsed_delta, parsed_label, ok = ra._parse_window(value)
    assert ok is True
    assert parsed_delta == delta
    assert parsed_label == label


@pytest.mark.parametrize("value", ["", "abc", "10", "5x", None])
def test_parse_window_invalid_falls_back_to_1h(value) -> None:
    parsed_delta, parsed_label, ok = ra._parse_window(value)
    assert ok is False
    assert parsed_delta == timedelta(hours=1)
    assert parsed_label == "1h"


# -- _label / _parse_dt -------------------------------------------------


def test_label_accepts_dict_str_and_none() -> None:
    assert ra._label({"id": "x", "name": "Penha"}) == "Penha"
    assert ra._label("Centro") == "Centro"
    assert ra._label(None) is None
    assert ra._label("") is None


def test_parse_dt_invalid_returns_none() -> None:
    assert ra._parse_dt("xxx") is None
    assert ra._parse_dt(None) is None


# -- _normalize ---------------------------------------------------------


def test_normalize_counts_victims_and_deaths() -> None:
    occ = _occ(
        10,
        policeAction=True,
        agentPresence=True,
        victims=[
            {"situation": "dead", "deathDate": None},
            {"situation": "injured", "deathDate": None},
            {"situation": None, "deathDate": "2026-06-17"},
        ],
        transports=[{"interruptedTransport": True}],
    )
    normalized = ra._normalize(occ)
    assert isinstance(normalized, RecentOccurrence)
    assert normalized.victims_count == 3
    assert normalized.deaths_count == 2  # "dead" plus a present deathDate.
    assert normalized.police_action is True
    assert normalized.agent_presence is True
    assert normalized.transport_interrupted is True
    assert normalized.neighborhood == "Penha"
    assert normalized.main_reason == "Police operation"


def test_normalize_does_not_expose_coordinates() -> None:
    normalized = ra._normalize(_occ(5, latitude="-22.9", longitude="-43.2"))
    assert not hasattr(normalized, "latitude")
    assert "latitude" not in normalized.model_dump()


# -- _assess ------------------------------------------------------------


def _recent(minutes_ago: int, **over: Any) -> RecentOccurrence:
    return ra._normalize(_occ(minutes_ago, **over))


def test_assess_without_occurrences() -> None:
    evidence, confidence, summary = ra._assess([], datetime.now(timezone.utc))
    assert evidence == "no recent evidence"
    assert confidence == "low"
    assert summary == "No recent records in the requested window."


def test_assess_high_evidence_by_volume() -> None:
    now = datetime.now(timezone.utc)
    recent = [_recent(200) for _ in range(5)]
    evidence, _confidence, _summary = ra._assess(recent, now)
    assert evidence == "high evidence"


def test_assess_high_evidence_by_recency() -> None:
    now = datetime.now(timezone.utc)
    recent = [_recent(10), _recent(20)]  # Two fresh records (<=60 min).
    evidence, confidence, _summary = ra._assess(recent, now)
    assert evidence == "high evidence"
    assert confidence == "medium"


def test_assess_moderate_without_recency() -> None:
    now = datetime.now(timezone.utc)
    recent = [_recent(120), _recent(200)]  # Two records, none fresh.
    evidence, _confidence, _summary = ra._assess(recent, now)
    assert evidence == "moderate evidence"


def test_assess_low_for_single_old_record() -> None:
    now = datetime.now(timezone.utc)
    recent = [_recent(300)]  # One record, older than 180 min.
    evidence, confidence, _summary = ra._assess(recent, now)
    assert evidence == "low evidence"
    assert confidence == "low"


# -- get_recent_activity -----------------------------------------------


async def test_get_recent_activity_happy_path() -> None:
    client = FakeClient(
        cities=[_city()],
        occurrences=[_occ(90), _occ(200)],
        last_update=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
    )
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="24h")

    assert result.occurrence_count == 2
    assert result.evidence_level == "moderate evidence"
    assert result.confidence_level == "medium"
    assert result.source_update_time == datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
    assert result.sources[0].name == "Fogo Cruzado"
    # The date filter sent to the API uses day-level granularity.
    assert "initialdate" in client.occurrence_calls[0]


async def test_get_recent_activity_filters_by_window() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30), _occ(200)])
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="1h")
    # Only the 30-minute-old occurrence is inside the 1h window.
    assert result.occurrence_count == 1


async def test_get_recent_activity_unknown_city() -> None:
    client = FakeClient(cities=[_city()], occurrences=[])
    result = await ra.get_recent_activity(client, city="Atlantis", time_window="1h")
    assert result.occurrence_count == 0
    assert result.evidence_level == "no evidence"
    assert "not found" in result.activity_summary
    assert not client.occurrence_calls  # It never reaches the occurrence query.


async def test_get_recent_activity_ambiguous_city() -> None:
    client = FakeClient(
        cities=[
            _city(city_id="c1", state="Rio de Janeiro"),
            _city(city_id="c2", state="Sao Paulo"),
        ],
        occurrences=[_occ(30)],
    )
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="6h")
    assert any("More than one city" in limit for limit in result.limitations)
    # The first match is used when the caller does not disambiguate.
    assert client.occurrence_calls[0]["idCities"] == "c1"


async def test_get_recent_activity_region_filter_without_match() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])  # Penha neighborhood.
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", region="Copacabana", time_window="6h"
    )
    assert result.occurrence_count == 0
    assert any("region 'Copacabana'" in limit for limit in result.limitations)


async def test_get_recent_activity_region_filter_with_match() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", region="penha", time_window="6h"
    )
    assert result.occurrence_count == 1


async def test_get_recent_activity_invalid_window_records_limitation() -> None:
    client = FakeClient(cities=[_city()], occurrences=[])
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="xyz")
    assert result.time_window == "1h"
    assert any("invalid" in limit for limit in result.limitations)


async def test_get_recent_activity_signals_next_page() -> None:
    client = FakeClient(
        cities=[_city()],
        occurrences=[_occ(30)],
        page_meta={"hasNextPage": True},
    )
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="24h")
    assert any("most recent" in limit for limit in result.limitations)


async def test_get_recent_activity_matches_city_without_accent() -> None:
    # Catalog has accents; unaccented user input must match through slugify.
    client = FakeClient(
        cities=[_city(name="S\u00e3o Gon\u00e7alo", city_id="sg")],
        occurrences=[_occ(30)],
    )
    result = await ra.get_recent_activity(client, city="sao goncalo", time_window="6h")
    assert client.occurrence_calls[0]["idCities"] == "sg"
    assert result.occurrence_count == 1


# -- territorial enrichment (Tier 1 / IBGE) ----------------------------


class FakeTerritory:
    """Stand-in for IbgeLocalidadesClient: returns canned municipalities or fails."""

    def __init__(self, municipalities=None, *, fail: bool = False) -> None:
        self._municipalities = municipalities or []
        self._fail = fail

    async def get_municipalities(self):
        if self._fail:
            raise RuntimeError("ibge unavailable")
        return self._municipalities


def _muni_rio():
    return {
        "id": 3304557,
        "nome": "Rio de Janeiro",
        "microrregiao": {
            "mesorregiao": {
                "UF": {"sigla": "RJ", "nome": "Rio de Janeiro", "regiao": {"nome": "Sudeste"}}
            }
        },
    }


async def test_enriches_with_territorial_context() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])
    territory = FakeTerritory([_muni_rio()])
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", time_window="6h", territory=territory
    )

    ctx = result.territorial_context
    assert ctx is not None
    assert ctx.ibge_city_code == 3304557
    assert ctx.uf == "RJ"
    assert ctx.macro_region == "Sudeste"
    assert ctx.match_quality == "exact"
    # The IBGE source is included in attribution when enrichment succeeds.
    assert any(s.name == "IBGE Localidades" for s in result.sources)


async def test_unavailable_territory_degrades_without_breaking() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])
    territory = FakeTerritory(fail=True)
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", time_window="6h", territory=territory
    )

    # The main response remains usable and records only a limitation.
    assert result.occurrence_count == 1
    assert result.territorial_context is None
    assert any("IBGE" in limit for limit in result.limitations)
    assert not any(s.name == "IBGE Localidades" for s in result.sources)


async def test_without_territory_does_not_enrich() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="6h")
    assert result.territorial_context is None


# -- COR.Rio corroboration (Tier 3, descriptive) -----------------------


class FakeCorroboration:
    """Substitutes CorRioClient: returns canned posts or fails."""

    def __init__(self, posts=None, *, fail: bool = False) -> None:
        self._posts = posts or []
        self._fail = fail

    async def get_recent_posts(self):
        if self._fail:
            raise RuntimeError("cor.rio down")
        return self._posts


def _cor_post(title: str = "Operação policial na Penha", excerpt: str = "Confronto na Penha"):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "title": {"rendered": title},
        "excerpt": {"rendered": excerpt},
        "date_gmt": now,
        "link": "https://cor.rio/x",
    }


async def test_corroboration_enriches_for_rio() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])  # Rio, Penha
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", time_window="6h",
        corroboration=FakeCorroboration([_cor_post()]),
    )
    assert len(result.corroborating_reports) == 1
    assert result.corroborating_reports[0].area == "penha"
    assert any(s.name == "COR.Rio" for s in result.sources)
    assert any("do not confirm" in limit for limit in result.limitations)


async def test_corroboration_skipped_for_non_rio() -> None:
    client = FakeClient(cities=[_city(name="Recife")], occurrences=[_occ(30)])
    result = await ra.get_recent_activity(
        client, city="Recife", time_window="6h",
        corroboration=FakeCorroboration([_cor_post()]),
    )
    assert result.corroborating_reports == []
    assert not any(s.name == "COR.Rio" for s in result.sources)


async def test_corroboration_drops_non_security_bulletin() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])  # Rio, Penha
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", time_window="6h",
        corroboration=FakeCorroboration(
            [_cor_post(title="Manutenção na Penha", excerpt="Obras na via")]
        ),
    )
    assert result.corroborating_reports == []
    assert not any(s.name == "COR.Rio" for s in result.sources)


async def test_corroboration_unavailable_adds_limitation() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", time_window="6h",
        corroboration=FakeCorroboration(fail=True),
    )
    assert result.corroborating_reports == []
    assert any("COR.Rio corroboration unavailable" in limit for limit in result.limitations)
