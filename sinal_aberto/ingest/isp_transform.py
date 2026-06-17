"""Pure transforms for the ISP monthly baseline (no network).

Input is the decoded text of ISP `BaseDPEvolucaoMensalCisp.csv` (semicolon
separated, one row per precinct/CISP per month). These functions aggregate to
municipality-month, build trailing-window averages, annualized per-100k rates,
cross-municipality percentiles, and the recent-vs-typical relative level.
"""

from __future__ import annotations

import csv
import io
from typing import Iterable, NamedTuple

TYPICAL_MONTHS = 12
RECENT_MONTHS = 6

# Required columns; looked up by header name so column order can change upstream.
_POLICE_COL = "hom_por_interv_policial"
_VIOLENT_COL = "letalidade_violenta"
_MUNIC_COL = "munic"
_YEAR_COL = "ano"
_MONTH_COL = "mes"


class IspRow(NamedTuple):
    municipality: str
    year: int
    month: int
    police_lethality: int
    violent_lethality: int


def _to_int(value: str | None) -> int:
    try:
        return int(float((value or "").strip().replace(",", ".")))
    except ValueError:
        return 0


def parse_isp_csv(text: str) -> list[IspRow]:
    """Parse the ISP CSV text into typed rows, skipping malformed lines."""
    reader = csv.reader(io.StringIO(text), delimiter=";")
    try:
        header = next(reader)
    except StopIteration:
        return []
    idx = {name.strip(): i for i, name in enumerate(header)}
    needed = (_MUNIC_COL, _YEAR_COL, _MONTH_COL, _POLICE_COL, _VIOLENT_COL)
    if any(col not in idx for col in needed):
        missing = [col for col in needed if col not in idx]
        raise ValueError(f"ISP CSV missing expected columns: {missing}")

    rows: list[IspRow] = []
    for fields in reader:
        if len(fields) <= idx[_VIOLENT_COL]:
            continue
        name = fields[idx[_MUNIC_COL]].strip()
        year = _to_int(fields[idx[_YEAR_COL]])
        month = _to_int(fields[idx[_MONTH_COL]])
        if not name or not (1 <= month <= 12) or year < 1990:
            continue
        rows.append(
            IspRow(
                municipality=name,
                year=year,
                month=month,
                police_lethality=_to_int(fields[idx[_POLICE_COL]]),
                violent_lethality=_to_int(fields[idx[_VIOLENT_COL]]),
            )
        )
    return rows


def month_ordinal(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def aggregate_municipality_month(
    rows: Iterable[IspRow],
) -> dict[str, dict[int, tuple[int, int]]]:
    """Sum across precincts: {municipality: {month_ordinal: (police, violent)}}."""
    out: dict[str, dict[int, tuple[int, int]]] = {}
    for row in rows:
        ordinal = month_ordinal(row.year, row.month)
        bucket = out.setdefault(row.municipality, {})
        police, violent = bucket.get(ordinal, (0, 0))
        bucket[ordinal] = (police + row.police_lethality, violent + row.violent_lethality)
    return out


def latest_ordinal(aggregated: dict[str, dict[int, tuple[int, int]]]) -> int | None:
    ordinals = [o for series in aggregated.values() for o in series]
    return max(ordinals) if ordinals else None


def window_average(
    series: dict[int, tuple[int, int]],
    latest: int,
    months: int,
    index: int,
) -> float:
    """Average monthly value of one indicator over the trailing window.

    Missing months count as zero (no record = no death), so the divisor is the
    fixed window length, not the number of present months.
    """
    low = latest - months + 1
    total = sum(v[index] for ordinal, v in series.items() if low <= ordinal <= latest)
    return total / months


def relative_level(recent_monthly: float, typical_monthly: float) -> str:
    """Recent vs the area's own typical level, as an ordinal band."""
    if typical_monthly <= 0:
        return "well above" if recent_monthly > 0 else "typical"
    ratio = recent_monthly / typical_monthly
    if ratio < 0.7:
        return "below"
    if ratio <= 1.3:
        return "typical"
    if ratio <= 2.0:
        return "above"
    return "well above"


def percentile_ranks(values: dict[int, float]) -> dict[int, float]:
    """Rank each value in [0,1] across the set (1.0 = highest), ties share the high rank."""
    if not values:
        return {}
    ordered = sorted(values.values())
    n = len(ordered)
    ranks: dict[int, float] = {}
    for key, value in values.items():
        # fraction of values <= this one
        count_le = sum(1 for v in ordered if v <= value)
        ranks[key] = round(count_le / n, 4)
    return ranks


def period_label(ordinal: int) -> str:
    """Human label 'YYYY-MM' for a month ordinal."""
    year, month = divmod(ordinal, 12)
    return f"{year:04d}-{month + 1:02d}"
