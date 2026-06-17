"""Configuracao do servidor MCP.

As credenciais do Fogo Cruzado sao lidas preferencialmente do arquivo `.env`
(chaves `user`/`password`, como ja usado nos testes de integracao). Variaveis de
ambiente especificas (`FOGOCRUZADO_*`) tem prioridade. Os nomes genericos
`user`/`password` sao lidos apenas do arquivo, nunca de `os.environ`, para evitar
colisao com variaveis do sistema (o Git Bash, por exemplo, define `USER`).
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import dotenv_values, find_dotenv
from pydantic import BaseModel

DEFAULT_BASE_URL = "https://api-service.fogocruzado.org.br/api/v2"
DEFAULT_IBGE_BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"

# Nomes lidos de os.environ (especificos, sem risco de colisao).
_EMAIL_ENV_NAMES = (
    "FOGOCRUZADO_EMAIL",
    "FOGO_CRUZADO_EMAIL",
    "FOGOCRUZADO_USER",
    "FOGO_CRUZADO_USER",
)
_PASSWORD_ENV_NAMES = ("FOGOCRUZADO_PASSWORD", "FOGO_CRUZADO_PASSWORD")
# Nomes genericos lidos apenas do arquivo .env.
_EMAIL_FILE_NAMES = ("user", "username", "email")
_PASSWORD_FILE_NAMES = ("password", "pass")


class Settings(BaseModel):
    fogocruzado_email: str
    fogocruzado_password: str
    fogocruzado_base_url: str = DEFAULT_BASE_URL
    ibge_base_url: str = DEFAULT_IBGE_BASE_URL
    http_timeout: float = 20.0
    occurrences_cache_ttl: float = 60.0
    catalog_cache_ttl: float = 300.0
    # A malha municipal do IBGE quase nao muda; cache longo (1 dia).
    ibge_cache_ttl: float = 86_400.0
    host: str = "127.0.0.1"
    port: int = 8000


def _resolve(env_names: tuple[str, ...], file_names: tuple[str, ...], file_values: dict) -> str | None:
    for name in env_names:
        value = os.getenv(name)
        if value:
            return value
    for name in file_names:
        value = file_values.get(name)
        if value:
            return value
    return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    file_values = dotenv_values(find_dotenv(usecwd=True))

    email = _resolve(_EMAIL_ENV_NAMES, _EMAIL_FILE_NAMES, file_values)
    password = _resolve(_PASSWORD_ENV_NAMES, _PASSWORD_FILE_NAMES, file_values)
    if not email or not password:
        raise RuntimeError(
            "Credenciais do Fogo Cruzado ausentes. Defina user/password "
            "(ou FOGOCRUZADO_EMAIL/FOGOCRUZADO_PASSWORD) no .env."
        )

    base_url = (
        os.getenv("FOGOCRUZADO_API_BASE_URL")
        or file_values.get("FOGOCRUZADO_API_BASE_URL")
        or DEFAULT_BASE_URL
    )
    ibge_base_url = (
        os.getenv("IBGE_API_BASE_URL")
        or file_values.get("IBGE_API_BASE_URL")
        or DEFAULT_IBGE_BASE_URL
    )

    return Settings(
        fogocruzado_email=email,
        fogocruzado_password=password,
        fogocruzado_base_url=base_url,
        ibge_base_url=ibge_base_url,
        host=os.getenv("SINAL_ABERTO_HOST", "127.0.0.1"),
        port=int(os.getenv("SINAL_ABERTO_PORT", "8000")),
    )
