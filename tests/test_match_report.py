from datetime import date, time

from vedic_astro.chart import build_kundali_chart
from vedic_astro.matching import compute_match_report
from vedic_astro.models import BirthData


def _bride_chart():
    return build_kundali_chart(
        BirthData(
            birth_date=date(1995, 3, 10),
            birth_time=time(6, 15, 0),
            latitude=13.0827,
            longitude=80.2707,  # Chennai
            utc_offset_hours=5.5,
        )
    )


def _groom_chart():
    return build_kundali_chart(
        BirthData(
            birth_date=date(1992, 11, 22),
            birth_time=time(14, 45, 0),
            latitude=12.9716,
            longitude=77.5946,  # Bengaluru
            utc_offset_hours=5.5,
        )
    )


def test_compute_match_report_has_all_eight_kootas() -> None:
    report = compute_match_report(_bride_chart(), _groom_chart())
    assert {k.name for k in report.kootas} == {
        "Varna", "Vashya", "Tara", "Yoni", "Graha Maitri", "Gana", "Bhakoot", "Nadi",
    }


def test_compute_match_report_total_matches_sum_of_kootas() -> None:
    report = compute_match_report(_bride_chart(), _groom_chart())
    assert report.total_points == sum(k.points_earned for k in report.kootas)
    assert 0 <= report.total_points <= 36


def test_compute_match_report_verdict_matches_total() -> None:
    report = compute_match_report(_bride_chart(), _groom_chart())
    if report.total_points >= 32:
        assert report.verdict == "Excellent match"
    elif report.total_points >= 24:
        assert report.verdict == "Good match"
    elif report.total_points >= 18:
        assert report.verdict == "Acceptable match"
    else:
        assert "Not recommended" in report.verdict


def test_compute_match_report_includes_mangal_dosha_for_both() -> None:
    report = compute_match_report(_bride_chart(), _groom_chart())
    assert report.bride_mangal_dosha.mars_house in range(1, 13)
    assert report.groom_mangal_dosha.mars_house in range(1, 13)
    assert report.mangal_dosha_compatible == (
        report.bride_mangal_dosha.has_dosha == report.groom_mangal_dosha.has_dosha
    )


def test_compute_match_report_identical_charts_score_full_except_nadi_and_tara() -> None:
    # Matching a chart against itself scores full marks on every koota except
    # Nadi and Tara: identical nakshatra necessarily means identical Nadi
    # group (Nadi Dosha, 0/8) and, by classical inclusive counting, your own
    # nakshatra counted from itself is "Janma" Tara - an inauspicious
    # category (0/3). Both are real, correct quirks of the system (matching
    # your astrological "twin" surfaces star-identity issues on two fronts),
    # not bugs.
    chart = _bride_chart()
    report = compute_match_report(chart, chart)
    by_name = {k.name: k for k in report.kootas}
    assert by_name["Nadi"].points_earned == 0
    assert by_name["Tara"].points_earned == 0
    for name, koota in by_name.items():
        if name not in ("Nadi", "Tara"):
            assert koota.points_earned == koota.max_points, name
    assert report.total_points == 25.0
