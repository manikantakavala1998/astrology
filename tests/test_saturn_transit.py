from datetime import date, datetime, time, timedelta

from vedic_astro.models import BirthData, NodeType, Sign, TransitSegment
from vedic_astro.saturn_transit import (
    compute_sade_sati_cycles,
    compute_saturn_transit_timeline,
    compute_transit_occurrences,
    scan_saturn_sign_segments,
)


def test_segments_cover_the_full_range_without_gaps() -> None:
    start = datetime(2021, 1, 1)
    end = datetime(2023, 1, 1)
    segments = scan_saturn_sign_segments(start, end, "lahiri", NodeType.MEAN)
    assert segments[0].start == start
    assert segments[-1].end == end
    for prev, nxt in zip(segments, segments[1:]):
        assert prev.end == nxt.start


def test_consecutive_segments_have_different_signs() -> None:
    start = datetime(2021, 1, 1)
    end = datetime(2023, 1, 1)
    segments = scan_saturn_sign_segments(start, end, "lahiri", NodeType.MEAN)
    for prev, nxt in zip(segments, segments[1:]):
        assert prev.sign != nxt.sign


def test_real_2022_retrograde_triple_crossing() -> None:
    # Empirically verified this session against real ephemeris data: Saturn
    # entered Aquarius 2022-05-01, retrograded back into Capricorn around
    # 2022-07-20, and re-entered Aquarius for good around 2023-01-26 -
    # a single sign boundary crossed three times in one retrograde episode.
    # A naive first-crossing-only detector would miss the second and third.
    start = datetime(2022, 1, 1)
    end = datetime(2023, 6, 1)
    segments = scan_saturn_sign_segments(start, end, "lahiri", NodeType.MEAN)

    aquarius_capricorn_segments = [
        s for s in segments if s.sign in (Sign.AQUARIUS, Sign.CAPRICORN)
    ]
    # Capricorn(pre) -> Aquarius -> Capricorn(retrograde) -> Aquarius(final)
    assert len(aquarius_capricorn_segments) >= 3

    # These reference dates come from a coarser 10-day-interval raw scan
    # (not a bisected exact crossing), so they're only accurate to within
    # that same ~10-day window - this checks the bisected crossings land
    # inside the right window, not that they match to the day.
    crossing_dates = sorted({s.start.date() for s in segments} | {s.end.date() for s in segments})
    expected_approx = [datetime(2022, 5, 1), datetime(2022, 7, 20), datetime(2023, 1, 26)]
    for expected in expected_approx:
        closest = min(crossing_dates, key=lambda d: abs((d - expected.date()).days))
        assert abs((closest - expected.date()).days) <= 10, (expected, closest)


def test_bisected_crossing_is_within_tolerance_of_a_finer_scan() -> None:
    # Cross-check the 5-day-step scan's bisected boundary against a much
    # finer 1-day-step scan over a short window around a known crossing.
    coarse = scan_saturn_sign_segments(
        datetime(2022, 4, 20), datetime(2022, 5, 15), "lahiri", NodeType.MEAN
    )
    fine = scan_saturn_sign_segments(
        datetime(2022, 4, 20), datetime(2022, 5, 15), "lahiri", NodeType.MEAN,
        step=timedelta(days=1),
    )
    coarse_crossing = next(s.end for s in coarse if s.sign == Sign.CAPRICORN)
    fine_crossing = next(s.end for s in fine if s.sign == Sign.CAPRICORN)
    assert abs((coarse_crossing - fine_crossing).total_seconds()) < 24 * 3600


def _seg(start_day: int, end_day: int, sign: Sign, base: datetime) -> TransitSegment:
    return TransitSegment(
        start=base + timedelta(days=start_day), end=base + timedelta(days=end_day), sign=sign
    )


def test_compute_sade_sati_cycles_normal_case_with_retrograde_revisit() -> None:
    # Moon in Leo -> trio is Cancer(phase1)/Leo(phase2)/Virgo(phase3).
    base = datetime(2000, 1, 1)
    scan_start = base
    scan_end = base + timedelta(days=2000)
    timeline = [
        _seg(0, 100, Sign.GEMINI, base),
        _seg(100, 300, Sign.CANCER, base),  # phase 1
        _seg(300, 500, Sign.LEO, base),  # phase 2
        _seg(500, 520, Sign.CANCER, base),  # retrograde dip back to phase 1
        _seg(520, 700, Sign.LEO, base),  # phase 2 again
        _seg(700, 900, Sign.VIRGO, base),  # phase 3
        _seg(900, 1000, Sign.LIBRA, base),  # exited the trio
    ]
    cycles = compute_sade_sati_cycles(timeline, Sign.LEO, scan_start, scan_end)
    assert len(cycles) == 1
    cycle = cycles[0]
    assert [s.phase for s in cycle.segments] == [1, 2, 1, 2, 3]
    assert cycle.start == base + timedelta(days=100)
    assert cycle.end == base + timedelta(days=900)
    assert cycle.truncated_at_start is False
    assert cycle.truncated_at_end is False


def test_compute_sade_sati_cycles_two_cycles_separated_by_a_large_gap() -> None:
    base = datetime(2000, 1, 1)
    scan_start = base
    scan_end = base + timedelta(days=365 * 40)
    timeline = [
        _seg(0, 200, Sign.CANCER, base),
        _seg(200, 400, Sign.LEO, base),
        _seg(400, 600, Sign.VIRGO, base),
        _seg(600, 365 * 35, Sign.LIBRA, base),  # ~34 years away from the trio
        _seg(365 * 35, 365 * 35 + 200, Sign.CANCER, base),
        _seg(365 * 35 + 200, 365 * 35 + 400, Sign.LEO, base),
        _seg(365 * 35 + 400, 365 * 40, Sign.VIRGO, base),
    ]
    cycles = compute_sade_sati_cycles(timeline, Sign.LEO, scan_start, scan_end)
    assert len(cycles) == 2


def test_compute_sade_sati_cycles_truncated_at_scan_start() -> None:
    # Saturn was already mid-phase-2 at birth (the scan window's own start).
    base = datetime(2000, 1, 1)
    scan_start = base
    scan_end = base + timedelta(days=1000)
    timeline = [
        _seg(0, 200, Sign.LEO, base),  # phase 2, starts exactly at scan_start
        _seg(200, 400, Sign.VIRGO, base),  # phase 3
        _seg(400, 1000, Sign.LIBRA, base),
    ]
    cycles = compute_sade_sati_cycles(timeline, Sign.LEO, scan_start, scan_end)
    assert len(cycles) == 1
    assert cycles[0].truncated_at_start is True
    assert cycles[0].truncated_at_end is False


def test_compute_transit_occurrences_clusters_single_sign_episodes() -> None:
    base = datetime(2000, 1, 1)
    scan_start = base
    scan_end = base + timedelta(days=365 * 30)
    timeline = [
        _seg(0, 100, Sign.ARIES, base),
        _seg(100, 300, Sign.CANCER, base),  # target episode 1 (with a retrograde revisit)
        _seg(300, 320, Sign.GEMINI, base),
        _seg(320, 500, Sign.CANCER, base),  # still episode 1 (small gap)
        _seg(500, 365 * 25, Sign.LIBRA, base),  # ~24 years elsewhere
        _seg(365 * 25, 365 * 25 + 200, Sign.CANCER, base),  # episode 2, a new cycle later
        _seg(365 * 25 + 200, 365 * 30, Sign.LIBRA, base),
    ]
    occurrences = compute_transit_occurrences(timeline, Sign.CANCER, scan_start, scan_end)
    assert len(occurrences) == 2
    assert len(occurrences[0].segments) == 2  # the two Cancer segments merged into one episode
    assert len(occurrences[1].segments) == 1


def test_compute_saturn_transit_timeline_end_to_end() -> None:
    birth_data = BirthData(
        birth_date=date(1990, 6, 15),
        birth_time=time(8, 30, 0),
        latitude=13.0827,
        longitude=80.2707,
        utc_offset_hours=5.5,
    )
    timeline = compute_saturn_transit_timeline(birth_data, moon_sign=Sign.AQUARIUS, ascendant_sign=Sign.CANCER)
    assert timeline.scan_start == birth_data.local_datetime
    assert (timeline.scan_end - timeline.scan_start).days > 365 * 99
    assert len(timeline.kantaka_shani_from_moon) == 3
    assert {h.house for h in timeline.kantaka_shani_from_moon} == {4, 7, 10}
    assert len(timeline.kantaka_shani_from_lagna) == 3
    # Over a 100-year lifetime, every one of these should occur at least once.
    assert len(timeline.sade_sati_cycles) >= 2
    assert len(timeline.ashtama_shani_transit) >= 2
