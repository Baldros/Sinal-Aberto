"""Teste de conexao: GPS SPPO (dados.mobilidade.rio).

Fonte auxiliar de contexto operacional de mobilidade. Validada em
docs/validacao-fontes-secundarias.md (2026-06-12). Sem autenticacao.

A validacao exige sempre uma janela temporal curta: sem filtro a resposta
passa de 90 MB. A janela e gerada dinamicamente no horario de Sao Paulo, em
vez de datas fixas, usando datetime da stdlib.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest


pytestmark = pytest.mark.integration

ENDPOINT = "https://dados.mobilidade.rio/gps/sppo"
# Sao Paulo e UTC-3 fixo: o Brasil aboliu o horario de verao em 2019. Usamos
# offset fixo via datetime para nao depender da base IANA (tzdata), que nao
# acompanha o Python no Windows.
RIO_TZ = timezone(timedelta(hours=-3))
API_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Campos minimos esperados em cada amostra de GPS, conforme a validacao.
SAMPLE_KEYS = {"ordem", "latitude", "longitude", "datahora", "linha"}


def _janela_recente(minutos: int = 5, atraso: int = 2) -> dict[str, str]:
    """Janela curta terminando alguns minutos atras (folga de ingestao)."""
    fim = datetime.now(RIO_TZ) - timedelta(minutes=atraso)
    inicio = fim - timedelta(minutes=minutos)
    return {
        "dataInicial": inicio.strftime(API_DATETIME_FORMAT),
        "dataFinal": fim.strftime(API_DATETIME_FORMAT),
    }


def test_janela_curta_responde_json(http_client: httpx.Client) -> None:
    response = http_client.get(ENDPOINT, params=_janela_recente())

    assert response.status_code == 200, (
        f"GPS SPPO respondeu status={response.status_code}"
    )
    # O Content-Type vem como text/html, mas o corpo e JSON; parse direto.
    payload = response.json()
    assert isinstance(payload, list), "GPS SPPO deveria retornar uma lista JSON"

    # Pode vir vazio em horarios de baixa operacao; so validamos o contrato
    # quando houver amostras.
    if payload:
        assert SAMPLE_KEYS <= set(payload[0]), (
            f"Amostra de GPS sem campos esperados: {SAMPLE_KEYS - set(payload[0])}"
        )
