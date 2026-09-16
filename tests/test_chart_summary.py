from datetime import date, time

from vedic_astro.chart import build_kundali_chart
from vedic_astro.matching import compute_match_report
from vedic_astro.models import BirthData
from vedic_astro.rag.chart_summary import summarize_chart, summarize_match


def _bride_chart():
    return build_kundali_chart(
        BirthData(
            birth_date=date(1995, 3, 10),
            birth_time=time(6, 15, 0),
            latitude=13.0827,
            longitude=80.2707,
            utc_offset_hours=5.5,
        )
    )


def _groom_chart():
    return build_kundali_chart(
        BirthData(
            birth_date=date(1992, 11, 22),
            birth_time=time(14, 45, 0),
            latitude=12.9716,
            longitude=77.5946,
            utc_offset_hours=5.5,
        )
    )


def test_summarize_chart_includes_ascendant_and_all_planets() -> None:
    chart = _bride_chart()
    summary = summarize_chart(chart, chart.birth_data.local_datetime)
    assert "Ascendant (Lagna)" in summary
    for planet in chart.planets:
        assert planet.planet.value in summary


def test_summarize_chart_includes_current_dasha_at_reference_time() -> None:
    chart = _bride_chart()
    reference = chart.dasha.periods[2].start  # well within the 3rd mahadasha
    summary = summarize_chart(chart, reference)
    expected_lord = chart.dasha.periods[2].planet.value
    assert f"mahadasha {expected_lord}" in summary


def test_summarize_chart_includes_panchanga() -> None:
    chart = _bride_chart()
    summary = summarize_chart(chart, chart.birth_data.local_datetime)
    assert chart.panchanga.tithi.name in summary
    assert chart.panchanga.nakshatra.name in summary


def test_summarize_match_includes_all_kootas_and_verdict() -> None:
    report = compute_match_report(_bride_chart(), _groom_chart())
    summary = summarize_match(report)
    for koota in report.kootas:
        assert koota.name in summary
    assert report.verdict in summary
    assert "Mangal Dosha" in summary
