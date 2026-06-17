"""Tests for credential resolution in config.

Focus on the sensitive rule: generic names (`user`/`password`) may come only
from `.env`, never from `os.environ`, so they cannot collide with system
variables.
"""

import pytest

from sinal_aberto.config import _resolve

ENV_NAMES = ("FOGOCRUZADO_EMAIL", "FOGO_CRUZADO_EMAIL")
FILE_NAMES = ("user", "username")


def test_prefers_specific_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOGOCRUZADO_EMAIL", "env@example.com")
    resolved = _resolve(ENV_NAMES, FILE_NAMES, {"user": "file@example.com"})
    assert resolved == "env@example.com"


def test_falls_back_to_file_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    resolved = _resolve(ENV_NAMES, FILE_NAMES, {"user": "file@example.com"})
    assert resolved == "file@example.com"


def test_generic_name_does_not_come_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # `user` may exist in os.environ, but it is not present in the dotenv values;
    # the resolver must return None instead of the operating-system username.
    monkeypatch.setenv("USER", "os-login")
    monkeypatch.setenv("user", "os-login")
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    resolved = _resolve(ENV_NAMES, FILE_NAMES, {})
    assert resolved is None


def test_returns_none_when_nothing_found(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    assert _resolve(ENV_NAMES, FILE_NAMES, {}) is None
