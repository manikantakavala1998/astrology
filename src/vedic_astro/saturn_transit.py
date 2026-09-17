"""Saturn transit timeline: Sade Sati, Kantaka Shani, transit Ashtama
Shani.

Genuinely new territory for this engine - everything else computed so far
is a birth-moment snapshot; this scans Saturn's position across a ~100
year date range. Performance and correctness were both empirically
verified before this was built: a 100-year, 5-day-step scan costs ~0.45s
(affordable for this synchronous, single-request-renders-everything app),
and Saturn's retrograde motion can cross the same sign boundary three
times within one retrograde episode (confirmed against real 2022
ephemeris data - see test_saturn_transit.py) - a naive first-crossing-only
detector would miss real transit events, so this module's scanner tracks
every crossing, not just the first.

5-day sampling is provably safe at Saturn's real motion: its station-to-
station cadence is ~4.5 months and its fastest direct motion is only
~0.13 degrees/day, so a full "cross a boundary, station, cross back"
round-trip cannot fit inside one 5-day window - every real crossing
always shows up as a sign mismatch between two adjacent samples, and
standard time-based bisection (direction-agnostic - it just narrows in on
the moment the sign changed, whichever way Saturn was moving) converges
correctly to it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from vedic_astro.ephemeris import planet_positions
from vedic_astro.models import (
    BirthData,
    KantakaShaniHouse,
    NodeType,
    Planet,
    SadeSatiCycle,
    SadeSatiSegment,
    Sign,
    SIGNS_IN_ORDER,
    SaturnTransitTimeline,
    TransitOccurrence,
    TransitSegment,
)
from vedic_astro.rashi_bhava import sign_for_longitude

SAMPLE_STEP = timedelta(days=5)
BISECTION_TOLERANCE = timedelta(hours=6)
SCAN_YEARS = 100
DAYS_PER_YEAR = 365.2425  # matches dasha.py/jaimini.py convention

# Two consecutive occurrences of the same target sign(s) belong to the same
# cycle/occurrence if the gap between them is under this threshold. A
# retrograde dip out and back is bounded by roughly Saturn's own
# retrograde-episode length (~140 days) plus a modest return, safely under
# 1.5 years even pathologically; the next real cycle is ~29.5 years away.
# 3 years sits with enormous margin between those two regimes.
CLUSTER_GAP_THRESHOLD = timedelta(days=365 * 3)


def _saturn_sign(utc_dt: datetime, ayanamsha: str, node_type: NodeType) -> Sign:
    positions = planet_positions(utc_dt, ayanamsha, node_type)
    return sign_for_longitude(positions[Planet.SATURN].longitude)


def _bisect_crossing(
    left: datetime, right: datetime, left_sign: Sign, ayanamsha: str, node_type: NodeType
) -> datetime:
    """The moment (within BISECTION_TOLERANCE) Saturn's sign changed away
    from `left_sign`, somewhere in (left, right]. Assumes exactly one
    crossing in this window - guaranteed by the 5-day sampling step being
    far shorter than Saturn's station-to-station cadence (see module
    docstring)."""
    while right - left > BISECTION_TOLERANCE:
        mid = left + (right - left) / 2
        if _saturn_sign(mid, ayanamsha, node_type) == left_sign:
            left = mid
        else:
            right = mid
    return right


def scan_saturn_sign_segments(
    start: datetime,
    end: datetime,
    ayanamsha: str,
    node_type: NodeType,
    step: timedelta = SAMPLE_STEP,
) -> list[TransitSegment]:
    """Ordered, contiguous TransitSegments covering [start, end] - each one
    a maximal same-sign span. Consecutive segments always have different
    signs by construction."""
    samples: list[tuple[datetime, Sign]] = []
    cursor = start
    while cursor < end:
        samples.append((cursor, _saturn_sign(cursor, ayanamsha, node_type)))
        cursor += step
    samples.append((end, _saturn_sign(end, ayanamsha, node_type)))

    segments: list[TransitSegment] = []
    segment_start = samples[0][0]
    segment_sign = samples[0][1]
    for (prev_dt, prev_sign), (next_dt, next_sign) in zip(samples, samples[1:]):
        if next_sign != prev_sign:
            crossing = _bisect_crossing(prev_dt, next_dt, prev_sign, ayanamsha, node_type)
            segments.append(TransitSegment(start=segment_start, end=crossing, sign=segment_sign))
            segment_start = crossing
            segment_sign = next_sign
    segments.append(TransitSegment(start=segment_start, end=end, sign=segment_sign))
    return segments


def _cluster_episodes(
    segments: list[TransitSegment],
    in_target: Callable[[Sign], bool],
    gap_threshold: timedelta,
) -> list[list[TransitSegment]]:
    """Groups the segments whose sign satisfies `in_target` into clusters:
    two consecutive target segments belong to the same cluster if the gap
    between them (time spent in non-target signs) is under `gap_threshold`,
    otherwise a new cluster starts."""
    target_segments = [s for s in segments if in_target(s.sign)]
    if not target_segments:
        return []
    clusters: list[list[TransitSegment]] = [[target_segments[0]]]
    for prev, curr in zip(target_segments, target_segments[1:]):
        gap = curr.start - prev.end
        if gap < gap_threshold:
            clusters[-1].append(curr)
        else:
            clusters.append([curr])
    return clusters


def _sign_at_house_offset(base_sign: Sign, house: int) -> Sign:
    base_index = SIGNS_IN_ORDER.index(base_sign)
    return SIGNS_IN_ORDER[(base_index + house - 1) % 12]


def _sade_sati_phase(sign: Sign, phase1: Sign, phase2: Sign) -> int:
    if sign == phase1:
        return 1
    if sign == phase2:
        return 2
    return 3


def compute_sade_sati_cycles(
    master_timeline: list[TransitSegment], moon_sign: Sign, scan_start: datetime, scan_end: datetime
) -> list[SadeSatiCycle]:
    phase1 = _sign_at_house_offset(moon_sign, 12)  # sign immediately before Moon sign
    phase2 = moon_sign
    phase3 = _sign_at_house_offset(moon_sign, 2)  # sign immediately after Moon sign
    trio = {phase1, phase2, phase3}

    clusters = _cluster_episodes(master_timeline, lambda sign: sign in trio, CLUSTER_GAP_THRESHOLD)
    cycles: list[SadeSatiCycle] = []
    for cluster in clusters:
        sade_sati_segments = [
            SadeSatiSegment(phase=_sade_sati_phase(seg.sign, phase1, phase2), segment=seg)
            for seg in cluster
        ]
        cycles.append(
            SadeSatiCycle(
                segments=sade_sati_segments,
                start=cluster[0].start,
                end=cluster[-1].end,
                truncated_at_start=(cluster[0].start == scan_start),
                truncated_at_end=(cluster[-1].end == scan_end),
            )
        )
    return cycles


def compute_transit_occurrences(
    master_timeline: list[TransitSegment], target_sign: Sign, scan_start: datetime, scan_end: datetime
) -> list[TransitOccurrence]:
    clusters = _cluster_episodes(
        master_timeline, lambda sign: sign == target_sign, CLUSTER_GAP_THRESHOLD
    )
    return [
        TransitOccurrence(
            segments=cluster,
            start=cluster[0].start,
            end=cluster[-1].end,
            truncated_at_start=(cluster[0].start == scan_start),
            truncated_at_end=(cluster[-1].end == scan_end),
        )
        for cluster in clusters
    ]


def compute_saturn_transit_timeline(
    birth_data: BirthData, moon_sign: Sign, ascendant_sign: Sign
) -> SaturnTransitTimeline:
    """Scans Saturn once (birth -> birth+100 years) and derives Sade Sati,
    Kantaka Shani (from both Moon and Lagna, per the classical rule that
    considers either base sign), and transit Ashtama Shani from that same
    scan - see the module docstring for why this is safe/affordable.

    The scan itself runs in UTC (required for accurate ephemeris lookups);
    all returned dates are shifted back by the birth place's fixed UTC
    offset before any derivation, so everything downstream - and every
    date shown to the user - is in the birth place's local-equivalent
    time, consistent with how dasha.py's periods are anchored to
    birth_data.local_datetime rather than UTC.
    """
    utc_start = birth_data.utc_datetime
    utc_end = utc_start + timedelta(days=SCAN_YEARS * DAYS_PER_YEAR)
    utc_master_timeline = scan_saturn_sign_segments(
        utc_start, utc_end, birth_data.ayanamsha, birth_data.node_type
    )

    offset = timedelta(hours=birth_data.utc_offset_hours)
    master_timeline = [
        TransitSegment(start=seg.start + offset, end=seg.end + offset, sign=seg.sign)
        for seg in utc_master_timeline
    ]
    scan_start = utc_start + offset
    scan_end = utc_end + offset

    kantaka_from_moon = [
        KantakaShaniHouse(
            house=house,
            occurrences=compute_transit_occurrences(
                master_timeline, _sign_at_house_offset(moon_sign, house), scan_start, scan_end
            ),
        )
        for house in (4, 7, 10)
    ]
    kantaka_from_lagna = [
        KantakaShaniHouse(
            house=house,
            occurrences=compute_transit_occurrences(
                master_timeline, _sign_at_house_offset(ascendant_sign, house), scan_start, scan_end
            ),
        )
        for house in (4, 7, 10)
    ]
    ashtama_shani_transit = compute_transit_occurrences(
        master_timeline, _sign_at_house_offset(moon_sign, 8), scan_start, scan_end
    )

    return SaturnTransitTimeline(
        sade_sati_cycles=compute_sade_sati_cycles(master_timeline, moon_sign, scan_start, scan_end),
        kantaka_shani_from_moon=kantaka_from_moon,
        kantaka_shani_from_lagna=kantaka_from_lagna,
        ashtama_shani_transit=ashtama_shani_transit,
        scan_start=scan_start,
        scan_end=scan_end,
    )
