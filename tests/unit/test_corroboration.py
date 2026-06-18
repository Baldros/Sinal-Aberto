"""Tests for COR.Rio corroboration helpers, without network calls."""

from datetime import datetime, timedelta, timezone

from sinal_aberto.models import RecentOccurrence
from sinal_aberto.tools.corroboration import (
    collect_terms,
    match_reports,
    parse_wp_datetime,
    strip_html,
)

NOW = datetime(2026, 6, 17, 18, 0, tzinfo=timezone.utc)
DAY = timedelta(hours=24)


def _post(title: str, excerpt: str, *, date_gmt: str = "2026-06-17T15:00:00", link: str = "https://cor.rio/x"):
    return {
        "title": {"rendered": title},
        "excerpt": {"rendered": excerpt},
        "date_gmt": date_gmt,
        "link": link,
    }


# -- strip_html / parse_wp_datetime ------------------------------------


def test_strip_html_unescapes_and_compacts() -> None:
    assert strip_html("<p>Opera&ccedil;&atilde;o na Penha</p>") == "Operação na Penha"
    assert strip_html("<p>O&nbsp;Centro&nbsp;informa</p>") == "O Centro informa"
    assert strip_html(None) == ""


def test_parse_wp_datetime_treats_gmt_as_utc() -> None:
    post = {"date_gmt": "2026-06-17T15:05:07"}
    assert parse_wp_datetime(post) == datetime(2026, 6, 17, 15, 5, 7, tzinfo=timezone.utc)
    assert parse_wp_datetime({}) is None


# -- collect_terms -----------------------------------------------------


def test_collect_terms_from_region_and_occurrences() -> None:
    occ = RecentOccurrence(neighborhood="Penha", locality="Morro da Fé")
    terms = collect_terms("Copacabana", [occ])
    assert "copacabana" in terms
    assert "penha" in terms
    assert "morro da fe" in terms


# -- match_reports: security filter (the anti-bias guard) --------------


def test_security_bulletin_in_area_matches() -> None:
    posts = [_post("Operação policial na Penha", "Confronto na comunidade")]
    reports = match_reports(posts, {"penha"}, now=NOW, max_age=DAY)
    assert len(reports) == 1
    assert reports[0].area == "penha"
    assert reports[0].source == "COR.Rio"


def test_maintenance_bulletin_in_area_is_rejected() -> None:
    # Same area, but no security topic: must NOT corroborate a shooting.
    posts = [_post("Interdição para manutenção na Penha", "Obras na via, trânsito alterado")]
    assert match_reports(posts, {"penha"}, now=NOW, max_age=DAY) == []


def test_security_bulletin_in_other_area_is_rejected() -> None:
    posts = [_post("Operação policial na Tijuca", "Confronto na Tijuca")]
    assert match_reports(posts, {"penha"}, now=NOW, max_age=DAY) == []


def test_old_bulletin_outside_window_is_rejected() -> None:
    posts = [_post("Operação policial na Penha", "Confronto", date_gmt="2026-06-10T15:00:00")]
    assert match_reports(posts, {"penha"}, now=NOW, max_age=DAY) == []


def test_empty_terms_yields_no_reports() -> None:
    posts = [_post("Operação policial na Penha", "Confronto")]
    assert match_reports(posts, set(), now=NOW, max_age=DAY) == []


def test_limit_caps_results() -> None:
    posts = [_post(f"Operação policial na Penha {i}", "Confronto") for i in range(8)]
    reports = match_reports(posts, {"penha"}, now=NOW, max_age=DAY, limit=3)
    assert len(reports) == 3
