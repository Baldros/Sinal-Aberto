"""Connection test: GPS SPPO (dados.mobilidade.rio).

Auxiliary source for operational mobility context. Validated in
docs/validacao-fontes-secundarias.md (2026-06-12). No authentication.

Validation always requires a short time window: without filters the response
exceeds 90 MB. The window is generated dynamically in Sao Paulo time instead of
using fixed dates.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest


pytestmark = pytest.mark.integration

ENDPOINT = "https://dados.mobilidade.rio/gps/sppo"
# Sao Paulo is fixed UTC-3 for this purpose because Brazil abolished daylight
# saving time in 2019. A fixed datetime offset avoids depending on IANA tzdata,
# which is not bundled with Python on Windows.
RIO_TZ = timezone(timedelta(hours=-3))
API_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Minimum fields expected in each GPS sample, as documented in validation.
SAMPLE_KEYS = {"ordem", "latitude", "longitude", "datahora", "linha"}


def _recent_window(minutes: int = 5, delay: int = 2) -> dict[str, str]:
    """Short window ending a few minutes ago to allow ingestion lag."""
    end = datetime.now(RIO_TZ) - timedelta(minutes=delay)
    start = end - timedelta(minutes=minutes)
    return {
        "dataInicial": start.strftime(API_DATETIME_FORMAT),
        "dataFinal": end.strftime(API_DATETIME_FORMAT),
    }


def test_short_window_returns_json(http_client: httpx.Client) -> None:
    response = http_client.get(ENDPOINT, params=_recent_window())

    assert response.status_code == 200, (
        f"GPS SPPO returned status={response.status_code}"
    )
    # Content-Type is text/html, but the body is JSON; parse it directly.
    payload = response.json()
    assert isinstance(payload, list), "GPS SPPO should return a JSON list"

    # It can be empty during low-operation hours; validate the contract only
    # when samples are present.
    if payload:
        assert SAMPLE_KEYS <= set(payload[0]), (
            f"GPS sample missing expected fields: {SAMPLE_KEYS - set(payload[0])}"
        )
