"""Corroboration: match COR.Rio bulletins to the queried area and time.

Pure, offline functions: they take the raw WordPress posts (from CorRioClient)
plus the location terms of interest and return CorroboratingReport items. Matching
is by recency and by textual mention of a neighborhood/region, so the bulletins
returned are tied to where activity was actually asked about.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from ..models import CorroboratingReport, RecentOccurrence
from .territory import slugify

_TAG_RE = re.compile(r"<[^>]+>")
_SUMMARY_MAX = 280

# COR.Rio publishes about traffic, public works, weather and events as well as
# security. To avoid biasing the agent (a road-maintenance bulletin in the same
# neighborhood is NOT corroboration of a shooting), a bulletin must mention a
# security/operations topic to qualify. Slugified, accent-free, low-ambiguity
# terms; we err toward false negatives (omit a borderline bulletin) on purpose.
_SECURITY_TERMS = (
    "policia",  # policia, policial, policiais, policiamento
    "operacao policial",
    "tiroteio",
    "disparo",  # disparo(s) de arma
    "confronto",
    "balead",  # baleado/baleada/baleados
    "bala perdida",
    "seguranca publica",
    "homicidio",
    "chacina",
    "milicia",
    "trafico",  # distinct from "trafego" (traffic), which must not match
    "pmerj",
    "pcerj",
    "bope",
)


def _has_security_topic(haystack: str) -> bool:
    """True when the bulletin text plausibly concerns security/police operations."""
    return any(term in haystack for term in _SECURITY_TERMS)


def strip_html(text: str | None) -> str:
    """Plain text from a WordPress rendered field: drop tags, unescape, compact."""
    if not text:
        return ""
    no_tags = _TAG_RE.sub(" ", text)
    unescaped = html.unescape(no_tags).replace("\xa0", " ")
    return " ".join(unescaped.split())


def parse_wp_datetime(post: dict[str, Any]) -> datetime | None:
    """Publication time as UTC. WordPress date_gmt is UTC but carries no offset."""
    raw = post.get("date_gmt") or post.get("date")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _rendered(post: dict[str, Any], key: str) -> str:
    return strip_html((post.get(key) or {}).get("rendered"))


def collect_terms(
    region: str | None,
    occurrences: Iterable[RecentOccurrence],
) -> set[str]:
    """Location slugs to look for: the region filter plus occurrence areas."""
    terms: set[str] = set()
    region_slug = slugify(region)
    if region_slug:
        terms.add(region_slug)
    for occ in occurrences:
        for label in (occ.neighborhood, occ.sub_neighborhood, occ.locality):
            label_slug = slugify(label)
            if label_slug:
                terms.add(label_slug)
    return terms


def match_reports(
    posts: list[dict[str, Any]],
    terms: set[str],
    *,
    now: datetime,
    max_age: timedelta,
    limit: int = 5,
) -> list[CorroboratingReport]:
    """Recent security bulletins whose text mentions one of the terms, newest first.

    A bulletin qualifies only if it (1) is within max_age, (2) concerns a
    security/operations topic, and (3) mentions one of the area terms. Empty terms
    yields no reports: corroboration must be anchored to a place, never a generic
    dump of recent bulletins.
    """
    if not terms:
        return []
    cutoff = now - max_age
    reports: list[CorroboratingReport] = []
    for post in posts:
        published = parse_wp_datetime(post)
        if published is not None and published < cutoff:
            continue
        title = _rendered(post, "title")
        summary = _rendered(post, "excerpt")
        haystack = slugify(f"{title} {summary}")
        if not _has_security_topic(haystack):
            continue
        matched = next((term for term in terms if term in haystack), None)
        if matched is None:
            continue
        reports.append(
            CorroboratingReport(
                title=title or "(untitled)",
                area=matched,
                summary=summary[:_SUMMARY_MAX] or None,
                published_at=published,
                url=post.get("link"),
            )
        )
        if len(reports) >= limit:
            break
    return reports
