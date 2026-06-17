"""Testes da ferramenta get_recent_activity e seus helpers, sem rede."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from sinal_aberto.models import RecentOccurrence
from sinal_aberto.tools import recent_activity as ra


# -- helpers de fixtures -----------------------------------------------


class FakeClient:
    """Substitui FogoCruzadoClient: devolve dados canned, registra chamadas."""

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
        "contextInfo": {"mainReason": {"id": "r", "name": "Operacao policial"}},
        "transports": [],
        "victims": [],
        "animalVictims": [],
    }
    base.update(overrides)
    return base


# -- _parse_window -----------------------------------------------------


@pytest.mark.parametrize(
    "value,delta,label",
    [
        ("30m", timedelta(minutes=30), "30m"),
        ("1h", timedelta(hours=1), "1h"),
        ("24h", timedelta(hours=24), "24h"),
        ("2d", timedelta(days=2), "2d"),
    ],
)
def test_parse_window_valido(value: str, delta: timedelta, label: str) -> None:
    parsed_delta, parsed_label, ok = ra._parse_window(value)
    assert ok is True
    assert parsed_delta == delta
    assert parsed_label == label


@pytest.mark.parametrize("value", ["", "abc", "10", "5x", None])
def test_parse_window_invalido_cai_para_1h(value) -> None:
    parsed_delta, parsed_label, ok = ra._parse_window(value)
    assert ok is False
    assert parsed_delta == timedelta(hours=1)
    assert parsed_label == "1h"


# -- _label / _parse_dt ------------------------------------------------


def test_label_aceita_dict_str_e_none() -> None:
    assert ra._label({"id": "x", "name": "Penha"}) == "Penha"
    assert ra._label("Centro") == "Centro"
    assert ra._label(None) is None
    assert ra._label("") is None


def test_parse_dt_invalido_retorna_none() -> None:
    assert ra._parse_dt("xxx") is None
    assert ra._parse_dt(None) is None


# -- _normalize --------------------------------------------------------


def test_normalize_conta_vitimas_e_obitos() -> None:
    occ = _occ(
        10,
        policeAction=True,
        agentPresence=True,
        victims=[
            {"situation": "Morto", "deathDate": None},
            {"situation": "Ferido", "deathDate": None},
            {"situation": None, "deathDate": "2026-06-17"},
        ],
        transports=[{"interruptedTransport": True}],
    )
    normalized = ra._normalize(occ)
    assert isinstance(normalized, RecentOccurrence)
    assert normalized.victims_count == 3
    assert normalized.deaths_count == 2  # "Morto" + deathDate presente
    assert normalized.police_action is True
    assert normalized.agent_presence is True
    assert normalized.transport_interrupted is True
    assert normalized.neighborhood == "Penha"
    assert normalized.main_reason == "Operacao policial"


def test_normalize_nao_expoe_coordenadas() -> None:
    normalized = ra._normalize(_occ(5, latitude="-22.9", longitude="-43.2"))
    assert not hasattr(normalized, "latitude")
    assert "latitude" not in normalized.model_dump()


# -- _assess -----------------------------------------------------------


def _recent(minutes_ago: int, **over: Any) -> RecentOccurrence:
    return ra._normalize(_occ(minutes_ago, **over))


def test_assess_sem_ocorrencias() -> None:
    evidence, confidence, summary = ra._assess([], datetime.now(timezone.utc))
    assert evidence == "sem evidencia recente"
    assert confidence == "baixa"


def test_assess_alta_evidencia_por_volume() -> None:
    now = datetime.now(timezone.utc)
    recent = [_recent(200) for _ in range(5)]
    evidence, _confidence, _summary = ra._assess(recent, now)
    assert evidence == "alta evidencia"


def test_assess_alta_evidencia_por_recencia() -> None:
    now = datetime.now(timezone.utc)
    recent = [_recent(10), _recent(20)]  # 2 registros frescos (<=60 min)
    evidence, confidence, _summary = ra._assess(recent, now)
    assert evidence == "alta evidencia"
    assert confidence == "media"


def test_assess_moderada_sem_recencia() -> None:
    now = datetime.now(timezone.utc)
    recent = [_recent(120), _recent(200)]  # 2 registros, nenhum fresco
    evidence, _confidence, _summary = ra._assess(recent, now)
    assert evidence == "evidencia moderada"


def test_assess_baixa_para_registro_antigo_isolado() -> None:
    now = datetime.now(timezone.utc)
    recent = [_recent(300)]  # 1 registro, > 180 min
    evidence, confidence, _summary = ra._assess(recent, now)
    assert evidence == "baixa evidencia"
    assert confidence == "baixa"


# -- get_recent_activity ----------------------------------------------


async def test_get_recent_activity_caminho_feliz() -> None:
    client = FakeClient(
        cities=[_city()],
        occurrences=[_occ(90), _occ(200)],
        last_update=datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc),
    )
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="24h")

    assert result.occurrence_count == 2
    assert result.evidence_level == "evidencia moderada"
    assert result.confidence_level == "media"
    assert result.source_update_time == datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
    assert result.sources[0].name == "Fogo Cruzado"
    # o filtro de data enviado a API usa granularidade de dia
    assert "initialdate" in client.occurrence_calls[0]


async def test_get_recent_activity_filtra_por_janela() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30), _occ(200)])
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="1h")
    # so a ocorrencia de 30 min entra na janela de 1h
    assert result.occurrence_count == 1


async def test_get_recent_activity_cidade_inexistente() -> None:
    client = FakeClient(cities=[_city()], occurrences=[])
    result = await ra.get_recent_activity(client, city="Atlantida", time_window="1h")
    assert result.occurrence_count == 0
    assert result.evidence_level == "sem evidencia"
    assert "nao encontrada" in result.activity_summary
    assert not client.occurrence_calls  # nem chega a consultar ocorrencias


async def test_get_recent_activity_cidade_ambigua() -> None:
    client = FakeClient(
        cities=[
            _city(city_id="c1", state="Rio de Janeiro"),
            _city(city_id="c2", state="Sao Paulo"),
        ],
        occurrences=[_occ(30)],
    )
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="6h")
    assert any("Mais de uma cidade" in limit for limit in result.limitations)
    # usa a primeira correspondencia
    assert client.occurrence_calls[0]["idCities"] == "c1"


async def test_get_recent_activity_filtro_de_regiao_sem_match() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])  # bairro Penha
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", region="Copacabana", time_window="6h"
    )
    assert result.occurrence_count == 0
    assert any("regiao 'Copacabana'" in limit for limit in result.limitations)


async def test_get_recent_activity_filtro_de_regiao_com_match() -> None:
    client = FakeClient(cities=[_city()], occurrences=[_occ(30)])
    result = await ra.get_recent_activity(
        client, city="Rio de Janeiro", region="penha", time_window="6h"
    )
    assert result.occurrence_count == 1


async def test_get_recent_activity_janela_invalida_registra_limitacao() -> None:
    client = FakeClient(cities=[_city()], occurrences=[])
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="xyz")
    assert result.time_window == "1h"
    assert any("invalido" in limit for limit in result.limitations)


async def test_get_recent_activity_sinaliza_proxima_pagina() -> None:
    client = FakeClient(
        cities=[_city()],
        occurrences=[_occ(30)],
        page_meta={"hasNextPage": True},
    )
    result = await ra.get_recent_activity(client, city="Rio de Janeiro", time_window="24h")
    assert any("mais recentes" in limit for limit in result.limitations)
