"""Plain-text renderings of computed chart/match facts, used as exact
grounding context for the LLM - these are NOT retrieved via RAG, they're the
precise computed data passed straight into the prompt.
"""

from __future__ import annotations

from datetime import datetime

from vedic_astro.models import KundaliChart, MatchReport


def summarize_chart(chart: KundaliChart, reference_datetime: datetime) -> str:
    lines: list[str] = [
        f"Birth: {chart.birth_data.birth_date} at {chart.birth_data.birth_time}, "
        f"lat {chart.birth_data.latitude:.4f}, lon {chart.birth_data.longitude:.4f}, "
        f"UTC offset {chart.birth_data.utc_offset_hours:+.2f}",
        f"Ascendant (Lagna): {chart.ascendant.sign.value} at {chart.ascendant.degree_in_sign:.2f} degrees",
        "Planets:",
    ]
    for planet in chart.planets:
        retrograde = " (retrograde)" if planet.retrograde else ""
        navamsa = planet.navamsa_sign.value if planet.navamsa_sign else "unknown"
        if planet.hora_sign is not None and planet.hora_lord is not None:
            hora = f"{planet.hora_sign.value} ({planet.hora_lord.value})"
        else:
            hora = "unknown"
        lines.append(
            f"- {planet.planet.value}: {planet.sign.value} {planet.degree_in_sign:.2f} deg, "
            f"house {planet.house}, nakshatra {planet.nakshatra.name} pada {planet.nakshatra.pada}, "
            f"Navamsa sign {navamsa}, Hora sign {hora}{retrograde}"
        )

    lines.append(
        f"Panchanga at birth: Tithi {chart.panchanga.tithi.name} ({chart.panchanga.paksha} Paksha), "
        f"Vara {chart.panchanga.vara}, Nakshatra {chart.panchanga.nakshatra.name}, "
        f"Yoga {chart.panchanga.yoga.name}, Karana {chart.panchanga.karana.name}"
    )

    current_maha = chart.dasha.current_mahadasha(reference_datetime)
    current_antar = chart.dasha.current_antardasha(reference_datetime)
    if current_maha is not None:
        antar_text = f", antardasha {current_antar.planet.value}" if current_antar else ""
        lines.append(
            f"Current Vimshottari Dasha (as of {reference_datetime.date()}): "
            f"mahadasha {current_maha.planet.value} "
            f"({current_maha.start.date()} to {current_maha.end.date()}){antar_text}"
        )

    lines.append("Full Vimshottari Mahadasha timeline:")
    for period in chart.dasha.periods:
        lines.append(f"- {period.planet.value}: {period.start.date()} to {period.end.date()}")

    return "\n".join(lines)


def summarize_match(report: MatchReport) -> str:
    lines: list[str] = [
        f"Marriage compatibility (Ashtakoot Guna Milan): "
        f"{report.total_points}/{report.max_points} points - {report.verdict}",
        f"First person - Rasi: {report.bride_moon_sign.value}, Nakshatra: {report.bride_nakshatra}",
        f"Second person - Rasi: {report.groom_moon_sign.value}, Nakshatra: {report.groom_nakshatra}",
        "Koota breakdown:",
    ]
    for koota in report.kootas:
        lines.append(f"- {koota.name}: {koota.points_earned}/{koota.max_points} - {koota.reason}")
    lines.append(f"First person Mangal Dosha: {report.bride_mangal_dosha.reason}")
    lines.append(f"Second person Mangal Dosha: {report.groom_mangal_dosha.reason}")
    lines.append(
        "Mangal Dosha compatibility: "
        + ("compatible" if report.mangal_dosha_compatible else "mismatch")
    )
    return "\n".join(lines)
