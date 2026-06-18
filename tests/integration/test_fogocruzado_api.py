import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

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


@dataclass(frozen=True, repr=False)
class FogoCruzadoCredentials:
    email: str
    password: str


def _payload(response: httpx.Response, expected_status: int = 200) -> dict[str, Any]:
    assert response.status_code == expected_status, (
        f"Failed to query {response.request.url.path}: "
        f"status={response.status_code}"
    )
    payload = response.json()
    assert payload.get("code") == expected_status
    return payload


def _assert_keys(data: dict[str, Any], keys: set[str], label: str) -> None:
    assert keys <= set(data), f"{label} missing expected fields: {keys - set(data)}"


def _assert_reference_object(value: Any, label: str) -> None:
    assert isinstance(value, dict), f"{label} must be an object"
    _assert_keys(value, {"id", "name"}, label)


def _assert_page_meta(page_meta: dict[str, Any], page: int, take: int) -> None:
    _assert_keys(
        page_meta,
        {
            "page",
            "take",
            "itemCount",
            "pageCount",
            "hasPreviousPage",
            "hasNextPage",
        },
        "pageMeta",
    )
    assert page_meta["page"] == page
    assert page_meta["take"] == take
    assert isinstance(page_meta["hasPreviousPage"], bool)
    assert isinstance(page_meta["hasNextPage"], bool)


def _parse_api_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


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
def fogocruzado_credentials() -> FogoCruzadoCredentials:
    email = _first_config(EMAIL_ENV_NAMES, EMAIL_DOTENV_ONLY_NAMES)
    password = _first_config(PASSWORD_ENV_NAMES, PASSWORD_DOTENV_ONLY_NAMES)
    if not email or not password:
        pytest.skip(
            "Missing Fogo Cruzado credentials. Define "
            "FOGOCRUZADO_EMAIL and FOGOCRUZADO_PASSWORD in .env."
        )
    return FogoCruzadoCredentials(email=email, password=password)


@pytest.fixture(scope="session")
def fogocruzado_token(fogocruzado_credentials: FogoCruzadoCredentials) -> str:
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        response = client.post(
            "/auth/login",
            json={
                "email": fogocruzado_credentials.email,
                "password": fogocruzado_credentials.password,
            },
        )

    assert response.status_code == 201, (
        "Fogo Cruzado login failed: "
        f"status={response.status_code}"
    )
    payload = _payload(response, expected_status=201)
    token = payload.get("data", {}).get("accessToken")
    assert token, "Fogo Cruzado login did not return data.accessToken"
    return token


@pytest.fixture(scope="session")
def authenticated_client(fogocruzado_token: str):
    headers = {"Authorization": f"Bearer {fogocruzado_token}"}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=20.0) as client:
        yield client


@pytest.fixture(scope="session")
def states(authenticated_client: httpx.Client) -> list[dict[str, Any]]:
    response = authenticated_client.get("/states")
    payload = _payload(response)
    states = payload.get("data", [])
    assert states, "/states returned an empty list"
    return states


@pytest.fixture(scope="session")
def state_id(states: list[dict[str, Any]]) -> str:
    return states[0]["id"]


@pytest.fixture(scope="session")
def cities(authenticated_client: httpx.Client) -> list[dict[str, Any]]:
    response = authenticated_client.get("/cities")
    payload = _payload(response)
    cities = payload.get("data", [])
    assert cities, "/cities returned an empty list"
    return cities


@pytest.fixture(scope="session")
def first_city(cities: list[dict[str, Any]]) -> dict[str, Any]:
    return cities[0]


@pytest.fixture(scope="session")
def occurrence_page(
    authenticated_client: httpx.Client,
    state_id: str,
) -> tuple[httpx.Response, dict[str, Any]]:
    response = authenticated_client.get(
        "/occurrences",
        params={"page": 1, "take": 2, "order": "DESC", "idState": state_id},
    )
    return response, _payload(response)


@pytest.fixture(scope="session")
def first_occurrence(
    occurrence_page: tuple[httpx.Response, dict[str, Any]],
) -> dict[str, Any]:
    payload = occurrence_page[1]
    occurrences = payload.get("data", [])
    assert occurrences, "/occurrences returned an empty list"
    return occurrences[0]


@pytest.mark.integration
def test_login_returns_bearer_token(fogocruzado_token: str) -> None:
    assert isinstance(fogocruzado_token, str)
    assert len(fogocruzado_token) > 20


@pytest.mark.integration
def test_refresh_returns_bearer_token(
    fogocruzado_credentials: FogoCruzadoCredentials,
) -> None:
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        login_response = client.post(
            "/auth/login",
            json={
                "email": fogocruzado_credentials.email,
                "password": fogocruzado_credentials.password,
            },
        )
        login_payload = _payload(login_response, expected_status=201)
        token = login_payload["data"]["accessToken"]
        refresh_response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"},
            json={"accessToken": token},
        )

    refresh_payload = _payload(refresh_response, expected_status=201)
    refreshed_token = refresh_payload.get("data", {}).get("accessToken")
    expires_in = refresh_payload.get("data", {}).get("expiresIn")
    assert isinstance(refreshed_token, str)
    assert len(refreshed_token) > 20
    assert isinstance(expires_in, int)
    assert expires_in > 0


@pytest.mark.integration
def test_states_endpoint_contract(states: list[dict[str, Any]]) -> None:
    for state in states:
        _assert_keys(state, {"id", "name"}, "state")
        assert isinstance(state["id"], str)
        assert isinstance(state["name"], str)


@pytest.mark.integration
def test_cities_endpoint_contract(cities: list[dict[str, Any]]) -> None:
    for city in cities:
        _assert_keys(city, {"id", "name", "state"}, "city")
        assert isinstance(city["id"], str)
        assert isinstance(city["name"], str)
        _assert_reference_object(city["state"], "city.state")


@pytest.mark.integration
def test_cities_filter_by_city_id(
    authenticated_client: httpx.Client,
    first_city: dict[str, Any],
) -> None:
    city_id = first_city["id"]
    response = authenticated_client.get("/cities", params={"cityId": city_id})
    payload = _payload(response)
    data = payload.get("data", [])

    assert data, "/cities?cityId returned an empty list"
    assert all(city["id"] == city_id for city in data)


@pytest.mark.integration
def test_cities_filter_by_city_name(
    authenticated_client: httpx.Client,
    first_city: dict[str, Any],
) -> None:
    city_name = first_city["name"]
    response = authenticated_client.get("/cities", params={"cityName": city_name})
    payload = _payload(response)
    data = payload.get("data", [])

    assert data, "/cities?cityName returned an empty list"
    assert any(city["name"].casefold() == city_name.casefold() for city in data)


@pytest.mark.integration
def test_cities_filter_by_state_id(
    authenticated_client: httpx.Client,
    first_city: dict[str, Any],
) -> None:
    state_id = first_city["state"]["id"]
    response = authenticated_client.get("/cities", params={"stateId": state_id})
    payload = _payload(response)
    data = payload.get("data", [])

    assert data, "/cities?stateId returned an empty list"
    assert all(city["state"]["id"] == state_id for city in data)


@pytest.mark.integration
def test_occurrences_endpoint_contract(
    occurrence_page: tuple[httpx.Response, dict[str, Any]],
) -> None:
    response, payload = occurrence_page
    assert "x-last-update" in response.headers
    assert "x-last-update-state" in response.headers
    assert isinstance(payload.get("pageMeta"), dict)
    _assert_page_meta(payload["pageMeta"], page=1, take=2)
    assert isinstance(payload.get("data"), list)
    assert payload["data"], "/occurrences returned an empty list"
    first_occurrence = payload["data"][0]
    _assert_keys(
        first_occurrence,
        {
            "id",
            "documentNumber",
            "state",
            "city",
            "latitude",
            "longitude",
            "date",
            "contextInfo",
            "transports",
            "victims",
            "animalVictims",
        },
        "occurrence",
    )
    _assert_reference_object(first_occurrence["state"], "occurrence.state")
    _assert_reference_object(first_occurrence["city"], "occurrence.city")


@pytest.mark.integration
def test_occurrence_nested_contract(first_occurrence: dict[str, Any]) -> None:
    context_info = first_occurrence["contextInfo"]
    assert isinstance(context_info, dict)
    _assert_keys(
        context_info,
        {
            "mainReason",
            "complementaryReasons",
            "clippings",
            "massacre",
            "policeUnit",
        },
        "occurrence.contextInfo",
    )
    if context_info["mainReason"] is not None:
        _assert_reference_object(context_info["mainReason"], "contextInfo.mainReason")
    assert isinstance(context_info["complementaryReasons"], list)
    assert isinstance(context_info["clippings"], list)
    assert isinstance(context_info["massacre"], bool)

    assert isinstance(first_occurrence["transports"], list)
    if first_occurrence["transports"]:
        _assert_keys(
            first_occurrence["transports"][0],
            {
                "id",
                "occurrenceId",
                "transport",
                "interruptedTransport",
                "dateInterruption",
                "releaseDate",
                "transportDescription",
            },
            "occurrence.transports[0]",
        )

    assert isinstance(first_occurrence["victims"], list)
    if first_occurrence["victims"]:
        _assert_keys(
            first_occurrence["victims"][0],
            {
                "id",
                "occurrenceId",
                "type",
                "situation",
                "circumstances",
                "deathDate",
                "personType",
                "age",
                "ageGroup",
                "genre",
                "race",
                "place",
                "serviceStatus",
                "qualifications",
                "politicalPosition",
                "politicalStatus",
                "partie",
                "coorporation",
                "agentPosition",
                "agentStatus",
                "unit",
            },
            "occurrence.victims[0]",
        )

    assert isinstance(first_occurrence["animalVictims"], list)
    if first_occurrence["animalVictims"]:
        _assert_keys(
            first_occurrence["animalVictims"][0],
            {
                "id",
                "occurrenceId",
                "name",
                "type",
                "animalType",
                "situation",
                "circumstances",
                "deathDate",
            },
            "occurrence.animalVictims[0]",
        )


@pytest.mark.integration
def test_occurrences_pagination_contract(
    authenticated_client: httpx.Client,
    state_id: str,
) -> None:
    response = authenticated_client.get(
        "/occurrences",
        params={"page": 1, "take": 1, "order": "DESC", "idState": state_id},
    )
    payload = _payload(response)
    _assert_page_meta(payload["pageMeta"], page=1, take=1)

    if payload["pageMeta"]["hasNextPage"]:
        next_response = authenticated_client.get(
            "/occurrences",
            params={"page": 2, "take": 1, "order": "DESC", "idState": state_id},
        )
        next_payload = _payload(next_response)
        _assert_page_meta(next_payload["pageMeta"], page=2, take=1)


@pytest.mark.integration
def test_occurrences_filter_by_date_range(
    authenticated_client: httpx.Client,
    first_occurrence: dict[str, Any],
    state_id: str,
) -> None:
    occurrence_date = _parse_api_date(first_occurrence["date"])
    initial_date = occurrence_date - timedelta(days=1)
    final_date = occurrence_date + timedelta(days=1)

    response = authenticated_client.get(
        "/occurrences",
        params={
            "page": 1,
            "take": 5,
            "order": "DESC",
            "idState": state_id,
            "initialdate": initial_date.isoformat(),
            "finaldate": final_date.isoformat(),
        },
    )
    payload = _payload(response)
    assert isinstance(payload.get("data"), list)
    assert payload["data"], "/occurrences with date filter returned an empty list"
    for occurrence in payload["data"]:
        found_date = _parse_api_date(occurrence["date"])
        assert initial_date <= found_date <= final_date


@pytest.mark.integration
def test_occurrences_filter_by_multiple_cities(
    authenticated_client: httpx.Client,
    occurrence_page: tuple[httpx.Response, dict[str, Any]],
    state_id: str,
) -> None:
    _, payload = occurrence_page
    city_ids = []
    for occurrence in payload["data"]:
        city_id = occurrence["city"]["id"]
        if city_id not in city_ids:
            city_ids.append(city_id)

    if len(city_ids) < 2:
        wider_response = authenticated_client.get(
            "/occurrences",
            params={"page": 1, "take": 50, "order": "DESC", "idState": state_id},
        )
        wider_payload = _payload(wider_response)
        for occurrence in wider_payload["data"]:
            city_id = occurrence["city"]["id"]
            if city_id not in city_ids:
                city_ids.append(city_id)
            if len(city_ids) >= 2:
                break

    if len(city_ids) < 2:
        pytest.skip("There are no recent occurrences in two different cities.")

    selected_city_ids = set(city_ids[:2])
    params = [
        ("page", "1"),
        ("take", "10"),
        ("order", "DESC"),
        ("idState", state_id),
        ("idCities", city_ids[0]),
        ("idCities", city_ids[1]),
    ]
    response = authenticated_client.get("/occurrences", params=params)
    filtered_payload = _payload(response)

    assert filtered_payload["data"], (
        "/occurrences with multiple idCities returned an empty list"
    )
    assert {
        occurrence["city"]["id"] for occurrence in filtered_payload["data"]
    } <= selected_city_ids


@pytest.mark.integration
def test_occurrences_filter_by_type_occurrence(
    authenticated_client: httpx.Client,
    state_id: str,
) -> None:
    response = authenticated_client.get(
        "/occurrences",
        params={
            "page": 1,
            "take": 1,
            "order": "DESC",
            "idState": state_id,
            "initialdate": "2018-01-01",
            "finaldate": date.today().isoformat(),
            "typeOccurrence": "withVictim",
        },
    )
    payload = _payload(response)

    assert isinstance(payload.get("data"), list)
    assert payload["data"], "/occurrences?typeOccurrence=withVictim returned empty"
    assert all(occurrence["victims"] for occurrence in payload["data"])
