from datetime import date, time

from vedic_astro.chart import build_kundali_chart
from vedic_astro.matching import compute_match_report
from vedic_astro.models import BirthData
from vedic_astro.rag.qa import answer_question


def _chart():
    return build_kundali_chart(
        BirthData(
            birth_date=date(1995, 3, 10),
            birth_time=time(6, 15, 0),
            latitude=13.0827,
            longitude=80.2707,
            utc_offset_hours=5.5,
        )
    )


def test_answer_question_mentions_actual_current_mahadasha() -> None:
    chart = _chart()
    reference = chart.dasha.periods[2].start
    expected_lord = chart.dasha.periods[2].planet.value

    answer = answer_question(
        "What is my current mahadasha and what does it generally mean?",
        chart,
        reference_datetime=reference,
    )
    assert expected_lord.lower() in answer.lower()


def test_answer_question_grounds_marriage_question_in_retrieved_notes() -> None:
    chart = _chart()
    answer = answer_question("What does Mars in the 7th house mean for marriage?", chart)
    # The sample knowledge base's Mangal Dosha / Mars-in-7th entry should be
    # retrieved and reflected in the answer.
    assert "dosha" in answer.lower() or "mangal" in answer.lower() or "mars" in answer.lower()


def test_answer_question_with_match_report_mentions_compatibility() -> None:
    bride = _chart()
    groom = build_kundali_chart(
        BirthData(
            birth_date=date(1992, 11, 22),
            birth_time=time(14, 45, 0),
            latitude=12.9716,
            longitude=77.5946,
            utc_offset_hours=5.5,
        )
    )
    report = compute_match_report(bride, groom)

    answer = answer_question(
        "Are we compatible for marriage based on our charts?",
        bride,
        match_report=report,
    )
    assert len(answer.strip()) > 0
    # A sane answer about compatibility should reference the verdict or score.
    assert any(word in answer.lower() for word in ("match", "compat", "point", "nadi", "dosha"))
