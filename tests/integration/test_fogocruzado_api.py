import os

import httpx
import pytest
from dotenv import dotenv_values, load_dotenv


load_dotenv()
DOTENV_VALUES = dotenv_values()

BASE_URL = os.getenv(
    "FOGOCRUZADO_API_BASE_URL",
    "https://api-service.fogocruzado.org.br/api/v2",
).rstrip("/")

EMAIL_ENV_NAMES = (
    "FOGOCRUZADO_EMAIL",
    "FOGO_CRUZADO_EMAIL",
    "FOGOCRUZADO_USER",
    "FOGO_CRUZADO_USER",
)
PASSWORD_ENV_NAMES = (
    "FOGOCRUZADO_PASSWORD",
    "FOGO_CRUZADO_PASSWORD",
)
EMAIL_DOTENV_ONLY_NAMES = (
    "EMAIL",
    "USER",
    "USERNAME",
    "email",
    "user",
    "username",
)
PASSWORD_DOTENV_ONLY_NAMES = (
    "PASSWORD",
    "PASS",
    "password",
    "pass",
)


def _first_config(
    names: tuple[str, ...],
    dotenv_only_names: tuple[str, ...] = (),
) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    for name in dotenv_only_names:
        value = DOTENV_VALUES.get(name)
        if value:
            return value
    return None


@pytest.fixture(scope="session")
def fogocruzado_credentials() -> tuple[str, str]:
    email = _first_config(EMAIL_ENV_NAMES, EMAIL_DOTENV_ONLY_NAMES)
    password = _first_config(PASSWORD_ENV_NAMES, PASSWORD_DOTENV_ONLY_NAMES)
    if not email or not password:
        pytest.skip(
            "Credenciais do Fogo Cruzado ausentes. Defina "
            "FOGOCRUZADO_EMAIL e FOGOCRUZADO_PASSWORD no .env."
        )
    return email, password


@pytest.fixture(scope="session")
def fogocruzado_token(fogocruzado_credentials: tuple[str, str]) -> str:
    email, password = fogocruzado_credentials
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )

    assert response.status_code == 201, (
        "Falha no login do Fogo Cruzado: "
        f"status={response.status_code}"
    )
    payload = response.json()
    token = payload.get("data", {}).get("accessToken")
    assert token, "Login do Fogo Cruzado nao retornou data.accessToken"
    return token


@pytest.fixture()
def authenticated_client(fogocruzado_token: str):
    headers = {"Authorization": f"Bearer {fogocruzado_token}"}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=20.0) as client:
        yield client


@pytest.fixture()
def state_id(authenticated_client: httpx.Client) -> str:
    response = authenticated_client.get("/states")
    assert response.status_code == 200, (
        "Falha ao consultar /states para preparar teste: "
        f"status={response.status_code}"
    )
    states = response.json().get("data", [])
    assert states, "/states retornou lista vazia"
    return states[0]["id"]


@pytest.mark.integration
def test_login_returns_bearer_token(fogocruzado_token: str) -> None:
    assert isinstance(fogocruzado_token, str)
    assert len(fogocruzado_token) > 20


@pytest.mark.integration
def test_states_endpoint_contract(authenticated_client: httpx.Client) -> None:
    response = authenticated_client.get("/states")

    assert response.status_code == 200, (
        "Falha ao consultar /states: "
        f"status={response.status_code}"
    )
    payload = response.json()
    assert payload.get("code") == 200
    assert isinstance(payload.get("data"), list)
    assert payload["data"], "/states retornou lista vazia"
    assert {"id", "name"} <= set(payload["data"][0])


@pytest.mark.integration
def test_cities_endpoint_contract(authenticated_client: httpx.Client) -> None:
    response = authenticated_client.get("/cities")

    assert response.status_code == 200, (
        "Falha ao consultar /cities: "
        f"status={response.status_code}"
    )
    payload = response.json()
    assert payload.get("code") == 200
    assert isinstance(payload.get("data"), list)
    assert payload["data"], "/cities retornou lista vazia"
    first_city = payload["data"][0]
    assert {"id", "name", "state"} <= set(first_city)
    assert {"id", "name"} <= set(first_city["state"])


@pytest.mark.integration
def test_occurrences_endpoint_contract(
    authenticated_client: httpx.Client,
    state_id: str,
) -> None:
    response = authenticated_client.get(
        "/occurrences",
        params={"page": 1, "take": 1, "order": "DESC", "idState": state_id},
    )

    assert response.status_code == 200, (
        "Falha ao consultar /occurrences: "
        f"status={response.status_code}"
    )
    payload = response.json()
    assert payload.get("code") == 200
    assert isinstance(payload.get("pageMeta"), dict)
    assert isinstance(payload.get("data"), list)
    assert payload["data"], "/occurrences retornou lista vazia"
    first_occurrence = payload["data"][0]
    assert {
        "id",
        "documentNumber",
        "state",
        "city",
        "latitude",
        "longitude",
        "date",
        "contextInfo",
        "victims",
    } <= set(first_occurrence)
