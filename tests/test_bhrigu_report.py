from datetime import date, datetime, time, timedelta

import pytest

from vedic_astro.bhrigu_report import anniversary, build_bhrigu_report
from vedic_astro.bsp import compute_bsp_rules
from vedic_astro.chart import build_kundali_chart
from vedic_astro.dasha import compute_deeper_sub_periods, DAYS_PER_YEAR
from vedic_astro.models import BirthData, Planet, Sign, PlanetPosition, NakshatraPlacement
from vedic_astro.padma_chakra import compute_padma_chakra_years


def position(planet, sign, house, degree=1.0):
    return PlanetPosition(planet=planet, sign=sign, house=house,
                          longitude=list(Sign).index(sign) * 30 + degree, degree_in_sign=degree,
                          nakshatra=NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU),
                          retrograde=False)


@pytest.fixture(scope="module")
def report():
    birth = BirthData(birth_date=date(1998, 9, 4), birth_time=time(0, 3),
                      latitude=17.00517, longitude=81.77784, utc_offset_hours=5.5)
    return build_bhrigu_report(build_kundali_chart(birth))


def test_empty_lagna_aspect_is_a_research_qualifier():
    # Cancer ascendant, Mars in Sagittarius H6: eighth aspect reaches empty H1.
    # No dignity, retrograde, kendra/trikona or special ascendant trigger.
    planets = [position(p, Sign.VIRGO, 3) for p in Planet if p != Planet.MARS]
    planets.append(position(Planet.MARS, Sign.SAGITTARIUS, 6))
    mars_rule = compute_bsp_rules(Sign.CANCER, planets, [])[0]
    assert mars_rule.special_status
    assert "Mars aspects (influences) the Ascendant" in mars_rule.special_status_reasons
    assert mars_rule.affected_house_from_lagna == 3


def test_original_bsp_rule_does_not_require_research_gate():
    # H11 Mars has no aspect to H1 or the Moon's H4, no qualifying dignity.
    planets = [position(p, Sign.LIBRA, 4) for p in Planet if p != Planet.MARS]
    planets.append(position(Planet.MARS, Sign.TAURUS, 11))
    gated = compute_bsp_rules(Sign.CANCER, planets, [])[0]
    original = compute_bsp_rules(Sign.CANCER, planets, [], require_special_status=False)[0]
    assert not gated.special_status and gated.affected_sign is None
    assert not original.special_status and original.affected_house_from_lagna == 8


def test_bsp_jupiter_targets_keep_distinct_roles(report):
    forty = next(r for r in report['bsp'] if r['rule_number'] == 10)
    assert [(t['house'], t['role']) for t in forty['targets']] == [(7, 'Primary activation'), (11, 'Occupied-house activation')]
    thirty_two = next(r for r in report['bsp'] if r['rule_number'] == 11)
    assert [(t['house'], t['role']) for t in thirty_two['targets']] == [(3, 'Primary activation'), (11, 'Occasional activation'), (5, 'Controlling influence')]
    assert not any(r['age'] == 29 for r in report['bsp'])


@pytest.mark.parametrize('venus_sign,expected', [(Sign.VIRGO, True), (Sign.SCORPIO, False)])
def test_d12_badhaka_is_mapped_by_sign_not_its_house_number(venus_sign, expected):
    planets = [position(p, Sign.ARIES, 12) for p in Planet if p != Planet.VENUS]
    planets.append(position(Planet.VENUS, venus_sign, 5 if expected else 7))
    # Taurus 26°52' => D12 Pisces. Its seventh is Virgo = D1 H5, not H7.
    result = compute_padma_chakra_years(Sign.TAURUS, 56.87, planets, datetime(1998, 9, 4), max_age=1)[0]
    assert result.is_badhaka is expected
    assert result.superimposed_house_from_lagna == (5 if expected else 7)


def test_birthday_and_padma_intervals_have_different_active_years(report):
    when = datetime(2026, 5, 1)
    bcp = next(r for r in report['bcp'] if datetime.fromisoformat(r['start']) <= when < datetime.fromisoformat(r['end']))
    padma = next(r for r in report['padma'] if datetime.fromisoformat(r['start_date']) <= when < datetime.fromisoformat(r['end_date']))
    assert bcp['age'] == 28 and padma['age'] == 29
    assert report['bcp'][28]['cycle_d1_house'] == 8
    assert report['badhakas'][1]['badhaka_sign'] == 'Virgo'
    assert report['badhakas'][1]['d1_house'] == 5
    for rows, start, end in ((report['bcp'], 'start', 'end'), (report['padma'], 'start_date', 'end_date')):
        assert len(rows) == 120
        assert all(r[start] < r[end] for r in rows)
        assert all(a[end] == b[start] for a, b in zip(rows, rows[1:]))


def test_birth_sample_keeps_annual_cycle_and_padma_frames_separate(report):
    bcp, padma = report['bcp'][28], report['padma'][28]
    assert (bcp['house_from_lagna'], bcp['sign_from_lagna'], bcp['year_lord']) == (5, 'Virgo', 'Mercury')
    assert (bcp['cycle_ruler'], bcp['house_from_cycle_ruler'], bcp['sign_from_cycle_ruler']) == ('Venus', 5, 'Sagittarius')
    assert bcp['cycle_d1_house'] == 8 and bcp['cycle_sign_lord'] == 'Jupiter'
    assert (padma['year_lord'], padma['year_lord_dwadasamsa_sign'], padma['superimposed_house_from_lagna']) == ('Mercury', 'Gemini', 2)


def test_leap_birth_anniversaries_keep_birth_time():
    birth = datetime(2000, 2, 29, 0, 3)
    assert anniversary(birth, 1) == datetime(2001, 2, 28, 0, 3)
    assert anniversary(birth, 4) == datetime(2004, 2, 29, 0, 3)


def test_aspects_include_empty_target_signs(report):
    aspect = next(a for a in report['aspects'] if a['planet'] == 'Jupiter' and a['offset'] == 7)
    assert aspect['source_sign'] == 'Pisces' and aspect['source_house'] == 11
    assert aspect['sign'] == 'Virgo' and aspect['house'] == 5 and aspect['planets'] == []


def active_path(report, when):
    rows = report['vimshottari']['periods']
    path = []
    for level in range(5):
        row = next(p for p in rows if datetime.fromisoformat(p['start']) <= when < datetime.fromisoformat(p['end']))
        path.append(row)
        if level == 4:
            break
        if row['sub_periods']:
            rows = row['sub_periods']
        else:
            start, end = datetime.fromisoformat(row['start']), datetime.fromisoformat(row['end'])
            children = compute_deeper_sub_periods(Planet(row['planet']), start, (end-start).total_seconds() / (DAYS_PER_YEAR * 86400), 1)
            children[-1].end = end
            rows = [p.model_dump(mode='json') for p in children]
    return path


def test_selected_five_levels_and_exact_boundary(report):
    path = active_path(report, datetime(2026, 10, 11, 13, 30))
    assert [p['planet'] for p in path] == ['Rahu', 'Venus', 'Sun', 'Mercury', 'Venus']
    prana_end = datetime.fromisoformat(path[-1]['end'])
    assert active_path(report, prana_end - timedelta(microseconds=1))[-1]['planet'] == 'Venus'
    assert active_path(report, prana_end)[-1]['planet'] == 'Sun'


def test_repeating_sequence_covers_entire_selectable_life(report):
    last_instant = datetime.fromisoformat(report['bcp'][-1]['end']) - timedelta(seconds=1)
    assert len(active_path(report, last_instant)) == 5
    assert report['bcp'][108]['cycle_ruler'] is None
    assert report['bcp'][119]['house_from_lagna'] == 12
