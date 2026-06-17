"""MCP server configuration.

Fogo Cruzado credentials are read from `.env` by default (`user`/`password`,
matching the integration tests). Specific environment variables
(`FOGOCRUZADO_*`) take precedence. Generic names such as `user`/`password` are
read only from the file, never from `os.environ`, to avoid collisions with
operating-system variables such as `USER`.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import dotenv_values, find_dotenv
from pydantic import BaseModel

DEFAULT_BASE_URL = "https://api-service.fogocruzado.org.br/api/v2"
DEFAULT_IBGE_BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"
DEFAULT_COR_RIO_BASE_URL = "https://cor.rio"

# Specific names are safe to read from os.environ because they belong to this app.
_EMAIL_ENV_NAMES = (
    "FOGOCRUZADO_EMAIL",
    "FOGO_CRUZADO_EMAIL",
    "FOGOCRUZADO_USER",
    "FOGO_CRUZADO_USER",
)
_PASSWORD_ENV_NAMES = ("FOGOCRUZADO_PASSWORD", "FOGO_CRUZADO_PASSWORD")
# Generic names are file-only so a shell login does not become an API username.
_EMAIL_FILE_NAMES = ("user", "username", "email")
_PASSWORD_FILE_NAMES = ("password", "pass")


class Settings(BaseModel):
    fogocruzado_email: str
    fogocruzado_password: str
    fogocruzado_base_url: str = DEFAULT_BASE_URL
    ibge_base_url: str = DEFAULT_IBGE_BASE_URL
    cor_rio_base_url: str = DEFAULT_COR_RIO_BASE_URL
    http_timeout: float = 20.0
    occurrences_cache_ttl: float = 60.0
    catalog_cache_ttl: float = 300.0
    # IBGE municipal metadata is effectively static for this workflow; cache it for one day.
    ibge_cache_ttl: float = 86_400.0
    # COR.Rio is a live feed; keep a short cache to absorb bursts.
    cor_rio_cache_ttl: float = 120.0
    host: str = "127.0.0.1"
    port: int = 8000


def _resolve(env_names: tuple[str, ...], file_names: tuple[str, ...], file_values: dict) -> str | None:
    """Resolve one setting with environment variables taking file-based precedence."""
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
    """Build the process-wide settings object once and reuse it across tool calls."""
    file_values = dotenv_values(find_dotenv(usecwd=True))

    email = _resolve(_EMAIL_ENV_NAMES, _EMAIL_FILE_NAMES, file_values)
    password = _resolve(_PASSWORD_ENV_NAMES, _PASSWORD_FILE_NAMES, file_values)
    if not email or not password:
        raise RuntimeError(
            "Missing Fogo Cruzado credentials. Define user/password "
            "(or FOGOCRUZADO_EMAIL/FOGOCRUZADO_PASSWORD) in .env."
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
    cor_rio_base_url = (
        os.getenv("COR_RIO_BASE_URL")
        or file_values.get("COR_RIO_BASE_URL")
        or DEFAULT_COR_RIO_BASE_URL
    )

    return Settings(
        fogocruzado_email=email,
        fogocruzado_password=password,
        fogocruzado_base_url=base_url,
        ibge_base_url=ibge_base_url,
        cor_rio_base_url=cor_rio_base_url,
        host=os.getenv("SINAL_ABERTO_HOST", "127.0.0.1"),
        port=int(os.getenv("SINAL_ABERTO_PORT", "8000")),
    )
