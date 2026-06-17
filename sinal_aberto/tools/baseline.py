"""Read the prepared ISP baseline file and build HistoricalBaseline lookups.

The file is produced offline by `sinal_aberto.ingest.build_isp_baseline` and read
read-only at runtime. The store degrades gracefully: if the file is absent or a
municipality is missing, lookups return None and the response simply omits the
baseline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import HistoricalBaseline, IndicatorBaseline

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "isp_baseline.json"


def _indicator(raw: dict[str, Any] | None) -> IndicatorBaseline:
    raw = raw or {}
    return IndicatorBaseline(
        typical_monthly=raw.get("typical_monthly"),
        recent_monthly=raw.get("recent_monthly"),
        per_100k_annual=raw.get("per_100k_annual"),
        percentile=raw.get("percentile"),
    )


def _pct(value: Any) -> str:
    try:
        return f"{round(float(value) * 100)}%"
    except (TypeError, ValueError):
        return "n/a"


def _build_note(entry: dict[str, Any], meta: dict[str, Any]) -> str:
    police = entry.get("police_lethality") or {}
    level = entry.get("relative_level", "indeterminate")
    typ = police.get("typical_monthly")
    rec = police.get("recent_monthly")
    parts = [f"Police lethality is {level} the area's own typical level"]
    if typ is not None and rec is not None:
        parts.append(f"typical ~{typ:.1f}/month, recent ~{rec:.1f}/month")
    if police.get("percentile") is not None:
        parts.append(f"top {_pct(police.get('percentile'))} of RJ municipalities per 100k")
    note = "; ".join(parts) + "."
    note += (
        " Under-reporting near communities means recorded police lethality is a "
        "floor, not the full picture; this is chronic context, not a live-event claim."
    )
    return note


class BaselineStore:
    def __init__(
        self,
        *,
        path: Path | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        if data is None:
            target = path or _DEFAULT_PATH
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
        self._municipalities: dict[str, Any] = data.get("municipalities", {})
        self._meta: dict[str, Any] = data.get("meta", {})

    def lookup(self, ibge_city_code: int) -> HistoricalBaseline | None:
        entry = self._municipalities.get(str(ibge_city_code))
        if not entry:
            return None
        return HistoricalBaseline(
            source=self._meta.get("source", "ISP Dados RJ"),
            ibge_city_code=ibge_city_code,
            population=entry.get("population"),
            police_lethality=_indicator(entry.get("police_lethality")),
            violent_lethality=_indicator(entry.get("violent_lethality")),
            relative_level=entry.get("relative_level", "indeterminate"),
            typical_window=self._meta.get("typical_window", "12 months"),
            recent_window=self._meta.get("recent_window", "6 months"),
            as_of=self._meta.get("as_of"),
            note=_build_note(entry, self._meta),
        )
