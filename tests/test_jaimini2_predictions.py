"""Prediction conditions must retain chart basis, method scope and real evidence."""
import pytest

from vedic_astro.chart import build_kundali_chart
from vedic_astro.jaimini2 import build_jaimini2_report
from vedic_astro.jaimini2_predictions import assess
from vedic_astro.models import BirthData


@pytest.fixture(scope='module')
def report():
    chart = build_kundali_chart(BirthData(birth_date='1998-09-04', birth_time='00:03:00',
                                        latitude=17.00517, longitude=81.77784, utc_offset_hours=5.5))
    return build_jaimini2_report(chart)


def test_no_support_is_not_treated_as_bad_and_opposing_signals_are_mixed():
    assert assess([])['tone'] == 'neutral'
    assert assess([{'present': False, 'tone': 'challenging'}])['tone'] == 'neutral'
    assert assess([{'present': True, 'tone': 'supportive'}])['tone'] == 'supportive'
    assert assess([{'present': True, 'tone': 'challenging'}])['tone'] == 'challenging'
    assert assess([{'present': True, 'tone': 'supportive'}, {'present': True, 'tone': 'challenging'}])['tone'] == 'mixed'
    assert assess([{'present': True, 'tone': 'mixed'}])['tone'] == 'mixed'


def test_all_requested_modules_and_arudha_connections_have_calculations(report):
    modules = report['predictions']['modules']
    assert [row['id'] for row in modules] == ['arudha', 'upapada', 'karakamsha', 'swamsha', 'yogada', 'kevala']
    assert len(modules[0]['padas']) == 12
    for module in modules:
        assert module['facts'] and module['basis'] in ('D1', 'D9')
        for condition in module['conditions']:
            assert condition['code'] and condition['summary'] and condition['evidence'] and condition['rule']
            assert isinstance(condition['present'], bool)


def test_karakamsha_and_swamsha_do_not_mix_d1_d9_occupation(report):
    modules = {row['id']: row for row in report['predictions']['modules']}
    karaka, swamsha = modules['karakamsha'], modules['swamsha']
    assert karaka['anchor'] == swamsha['anchor'] == 'Pisces'
    assert karaka['basis'] == 'D1' and swamsha['basis'] == 'D9'
    assert karaka['houses'][0]['occupants'] == 'Jupiter'
    assert swamsha['houses'][0]['occupants'] == 'Mercury'
    assert any('Jupiter' in row['evidence'] for row in karaka['conditions'])
    assert any('Mercury' in row['evidence'] for row in swamsha['conditions'])


def test_upapada_variants_are_separate_and_do_not_assume_gender(report):
    rows = report['predictions']['upapada_readings']
    assert len(rows) == 3 and rows[0]['title'] == 'Standard Upapada'
    assert rows[0]['anchor'] == report['upapada']['sign']
    assert [row['anchor'] for row in rows[1:]] == [row['sign'] for row in report['upapada_variants']]
    assert all(row['calculation'] and 'Sun is not counted' in row['notes'] for row in rows)


def test_yoga_predictions_only_use_qualified_planets_and_exclude_self_conjunction(report):
    modules = {row['id']: row for row in report['predictions']['modules']}
    for kind in ('yogada', 'kevala'):
        expected = {p for y in report['schemes']['7']['yogas'] if y['kind'] == kind and y['present'] for p in y['planets']}
        assert {group['planet'] for group in modules[kind]['groups']} == expected
    # Saturn is alone in Aries. Its own malefic nature must not create a conjunction.
    saturn = next(group for group in modules['kevala']['groups'] if group['planet'] == 'Saturn')
    assert not next(c for c in saturn['conditions'] if c['topic'] == 'Companion pressure')['present']
    assert saturn['tone'] == 'supportive'


def test_dasha_assessments_are_scoped_and_absent_rules_remain_unclassified(report):
    systems = {row['code']: row for row in report['dasha_systems']}
    assert systems['chara']['predictions']['Leo']['tone'] == 'mixed'  # Venus support plus Leo/Rahu pressure.
    assert systems['chara']['predictions']['Cancer']['tone'] == 'mixed'  # AK's occupied sign.
    assert systems['chara']['predictions']['Pisces']['tone'] == 'supportive'
    assert systems['navamsa']['predictions']['Leo']['tone'] == 'challenging'
    assert systems['navamsa']['predictions']['Scorpio']['tone'] == 'supportive'  # AmK Sun is Virgo in D9, H11.
    assert systems['navamsa']['predictions']['Aries']['tone'] == 'neutral'
    for system in systems.values():
        assert len(system['predictions']) == 12
        for row in system['predictions'].values():
            assert row['basis'] == system['basis']
            if system['code'] not in ('chara', 'navamsa', 'sthira', 'trikona', 'gochara'):
                assert row['tone'] == 'neutral' and not row['conditions']
    assert 'Transit-dependent' in systems['gochara']['predictions']['Aries']['scope']
