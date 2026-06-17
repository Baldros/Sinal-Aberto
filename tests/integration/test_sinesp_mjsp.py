"""Connection test: SINESP/MJSP (Brazilian Ministry of Justice CKAN).

Auxiliary source for aggregate national history. Validated in
docs/validacao-fontes-secundarias.md (2026-06-12). No authentication.
"""

from datetime import datetime

import httpx
import pytest


pytestmark = pytest.mark.integration

CKAN_PACKAGE_SHOW = "https://dados.mj.gov.br/api/3/action/package_show"
SINESP_PACKAGE_ID = "sistema-nacional-de-estatisticas-de-seguranca-publica"


@pytest.fixture(scope="module")
def sinesp_package(http_client: httpx.Client) -> dict:
    response = http_client.get(CKAN_PACKAGE_SHOW, params={"id": SINESP_PACKAGE_ID})
    assert response.status_code == 200, (
        f"CKAN MJSP returned status={response.status_code}"
    )
    payload = response.json()
    assert payload.get("success") is True
    return payload["result"]


def test_package_has_license_and_valid_date(sinesp_package: dict) -> None:
    # An open license was one criterion for using this source.
    license_id = (sinesp_package.get("license_id") or "").lower()
    license_title = (sinesp_package.get("license_title") or "").lower()
    assert "cc" in license_id or "creative commons" in license_title, (
        f"Unexpected license: id={license_id!r} title={license_title!r}"
    )

    # metadata_modified must be a real ISO timestamp; parse with stdlib instead
    # of comparing the raw string.
    modified = datetime.fromisoformat(sinesp_package["metadata_modified"])
    assert modified.year >= 2020


def test_package_has_zip_resource(sinesp_package: dict) -> None:
    resources = sinesp_package["resources"]
    assert isinstance(resources, list) and resources

    zip_resources = [
        resource
        for resource in resources
        if (resource.get("format") or "").upper() == "ZIP"
        or (resource.get("url") or "").lower().endswith(".zip")
    ]
    assert zip_resources, "SINESP exposes no ZIP resource"


def test_zip_resource_accessible(
    http_client: httpx.Client,
    sinesp_package: dict,
) -> None:
    # Derive the ZIP URL from CKAN itself because UUIDs change, then check only
    # headers; the file is dozens of MB.
    zip_url = next(
        resource["url"]
        for resource in sinesp_package["resources"]
        if (resource.get("format") or "").upper() == "ZIP"
        or (resource.get("url") or "").lower().endswith(".zip")
    )

    with http_client.stream("GET", zip_url) as response:
        assert response.status_code == 200, (
            f"SINESP ZIP returned status={response.status_code}"
        )
        content_type = response.headers.get("content-type", "").lower()
        assert "zip" in content_type or "octet-stream" in content_type, (
            f"Unexpected Content-Type for SINESP ZIP: {content_type!r}"
        )
