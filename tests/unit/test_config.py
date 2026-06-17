"""Testes de resolucao de credenciais em config.

Foco no ponto sensivel: nomes genericos (user/password) so podem vir do arquivo
.env, nunca de os.environ, para nao colidir com variaveis do sistema.
"""

import pytest

from sinal_aberto.config import _resolve

ENV_NAMES = ("FOGOCRUZADO_EMAIL", "FOGO_CRUZADO_EMAIL")
FILE_NAMES = ("user", "username")


def test_prefere_variavel_de_ambiente_especifica(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOGOCRUZADO_EMAIL", "env@example.com")
    resolved = _resolve(ENV_NAMES, FILE_NAMES, {"user": "file@example.com"})
    assert resolved == "env@example.com"


def test_cai_para_o_arquivo_quando_env_ausente(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    resolved = _resolve(ENV_NAMES, FILE_NAMES, {"user": "file@example.com"})
    assert resolved == "file@example.com"


def test_nome_generico_nao_vem_do_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    # 'user' existe em os.environ (Git Bash define USER), mas nao esta no arquivo:
    # deve resolver para None, nao para o usuario do sistema operacional.
    monkeypatch.setenv("USER", "login-do-so")
    monkeypatch.setenv("user", "login-do-so")
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    resolved = _resolve(ENV_NAMES, FILE_NAMES, {})
    assert resolved is None


def test_retorna_none_quando_nada_encontrado(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    assert _resolve(ENV_NAMES, FILE_NAMES, {}) is None
