"""Offline job: build the ISP baseline prepared file.

Run manually or on a schedule (never on a user request):

    ./.venv/Scripts/python.exe -m sinal_aberto.ingest.build_isp_baseline

It downloads the ISP monthly CSV, aggregates police and violent lethality to
municipality-month, maps municipalities to IBGE codes, fetches population from
SIDRA for per-100k rates and cross-municipality percentiles, and writes a small
JSON file the server reads read-only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ..tools.territory import slugify
from .isp_transform import (
    RECENT_MONTHS,
    TYPICAL_MONTHS,
    aggregate_municipality_month,
    latest_ordinal,
    parse_isp_csv,
    percentile_ranks,
    period_label,
    relative_level,
    window_average,
)

ISP_CSV_URL = "https://www.ispdados.rj.gov.br/Arquivos/BaseDPEvolucaoMensalCisp.csv"
IBGE_RJ_MUNI_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/RJ/municipios"
SIDRA_POP_URL = "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/last"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "isp_baseline.json"

# ISP spelling vs IBGE spelling (compared as slugs).
_ALIASES: dict[str, str] = {
    "parati": "paraty",
    "trajano de morais": "trajano de moraes",
    "bom jesus de itabapoana": "bom jesus do itabapoana",
}


def _download_isp_csv(client: httpx.Client) -> str:
    response = client.get(ISP_CSV_URL)
    response.raise_for_status()
    return response.content.decode("latin-1")


def _rj_municipalities(client: httpx.Client) -> dict[int, str]:
    """IBGE code -> canonical name for every RJ municipality."""
    response = client.get(IBGE_RJ_MUNI_URL)
    response.raise_for_status()
    return {int(m["id"]): m["nome"] for m in response.json()}


def _rj_population(client: httpx.Client) -> dict[int, int]:
    response = client.get(SIDRA_POP_URL)
    response.raise_for_status()
    rows = response.json()[1:]  # row 0 is header labels
    population: dict[int, int] = {}
    for row in rows:
        code = str(row.get("D1C", ""))
        if not code.startswith("33"):  # 33 = Rio de Janeiro state
            continue
        try:
            population[int(code)] = int(row["V"])
        except (TypeError, ValueError):
            continue
    return population


def _resolve_codes(name: str, name_to_code: dict[str, int]) -> list[int]:
    """Map an ISP municipality cell (possibly ';'-joined) to IBGE codes."""
    codes: list[int] = []
    for part in name.split(";"):
        slug = slugify(part)
        code = name_to_code.get(slug) or name_to_code.get(_ALIASES.get(slug, ""))
        if code is not None and code not in codes:
            codes.append(code)
    return codes


def _distribute(
    aggregated: dict[str, dict[int, tuple[int, int]]],
    name_to_code: dict[str, int],
    population: dict[int, int],
) -> tuple[dict[int, dict[int, tuple[float, float]]], list[str]]:
    """Re-key the name-based series to IBGE codes.

    Multi-municipality precincts (ISP joins their names with ';') are split across
    the listed municipalities, weighted by population (a larger municipality gets a
    larger share), so every municipality is covered without double counting.
    """
    by_code: dict[int, dict[int, tuple[float, float]]] = {}
    unmapped: list[str] = []
    for name, series in aggregated.items():
        codes = _resolve_codes(name, name_to_code)
        if not codes:
            unmapped.append(name)
            continue
        pops = [population.get(code, 0) for code in codes]
        total = sum(pops)
        weights = [p / total for p in pops] if total > 0 else [1 / len(codes)] * len(codes)
        for code, weight in zip(codes, weights):
            bucket = by_code.setdefault(code, {})
            for ordinal, (police, violent) in series.items():
                p0, v0 = bucket.get(ordinal, (0.0, 0.0))
                bucket[ordinal] = (p0 + police * weight, v0 + violent * weight)
    return by_code, unmapped


def build(client: httpx.Client) -> dict[str, Any]:
    rows = parse_isp_csv(_download_isp_csv(client))
    aggregated = aggregate_municipality_month(rows)
    latest = latest_ordinal(aggregated)
    if latest is None:
        raise RuntimeError("ISP data produced no usable rows")

    code_to_name = _rj_municipalities(client)
    name_to_code = {slugify(name): code for code, name in code_to_name.items()}
    population = _rj_population(client)
    by_code, unmapped = _distribute(aggregated, name_to_code, population)

    municipalities: dict[str, dict[str, Any]] = {}
    police_per_100k: dict[int, float] = {}
    violent_per_100k: dict[int, float] = {}

    for code, series in by_code.items():
        police_typ = window_average(series, latest, TYPICAL_MONTHS, 0)
        police_rec = window_average(series, latest, RECENT_MONTHS, 0)
        violent_typ = window_average(series, latest, TYPICAL_MONTHS, 1)
        violent_rec = window_average(series, latest, RECENT_MONTHS, 1)
        pop = population.get(code)

        def per_100k(monthly: float) -> float | None:
            if not pop:
                return None
            return round(monthly * 12 / pop * 100_000, 2)

        if pop:
            police_per_100k[code] = per_100k(police_typ) or 0.0
            violent_per_100k[code] = per_100k(violent_typ) or 0.0

        municipalities[str(code)] = {
            "name": code_to_name.get(code),
            "population": pop,
            "police_lethality": {
                "typical_monthly": round(police_typ, 3),
                "recent_monthly": round(police_rec, 3),
                "per_100k_annual": per_100k(police_typ),
            },
            "violent_lethality": {
                "typical_monthly": round(violent_typ, 3),
                "recent_monthly": round(violent_rec, 3),
                "per_100k_annual": per_100k(violent_typ),
            },
            "relative_level": relative_level(police_rec, police_typ),
        }

    for code, pct in percentile_ranks(police_per_100k).items():
        municipalities[str(code)]["police_lethality"]["percentile"] = pct
    for code, pct in percentile_ranks(violent_per_100k).items():
        municipalities[str(code)]["violent_lethality"]["percentile"] = pct

    if unmapped:
        print(f"WARNING: {len(unmapped)} unmapped entries: {sorted(set(unmapped))}")

    as_of = period_label(latest)
    return {
        "meta": {
            "source": "ISP Dados RJ",
            "as_of": as_of,
            "typical_window": f"{TYPICAL_MONTHS} months ending {as_of}",
            "recent_window": f"{RECENT_MONTHS} months ending {as_of}",
        },
        "municipalities": municipalities,
    }


def main() -> None:
    headers = {"User-Agent": "SinalAberto-Ingest/1.0 (+https://github.com/Sinal-Aberto)"}
    with httpx.Client(timeout=120.0, follow_redirects=True, headers=headers) as client:
        data = build(client)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    count = len(data["municipalities"])
    print(f"Wrote {OUTPUT_PATH} ({count} municipalities, as_of {data['meta']['as_of']}).")


if __name__ == "__main__":
    main()
