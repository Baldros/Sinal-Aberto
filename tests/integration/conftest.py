"""Fixtures compartilhadas dos testes de integracao de fontes auxiliares.

Cada fonte tem seu proprio arquivo de teste para isolar falhas, mas todas
reaproveitam o mesmo cliente HTTP configurado aqui.
"""

import httpx
import pytest


# Orgaos publicos as vezes respondem devagar; damos folga no read, mas mantemos
# o connect curto para falhar rapido quando o host estiver fora do ar.
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=15.0)
USER_AGENT = "SinalAberto-IntegrationTests/1.0 (+https://github.com/Sinal-Aberto)"


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    with httpx.Client(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        yield client
