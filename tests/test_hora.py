from datetime import date, datetime, time, timedelta

import pytest

from vedic_astro.hora import compute_birth_hora, hora_interval
from vedic_astro.models import BirthData, Planet
from vedic_astro.panchanga import compute_panchanga
from vedic_astro.shadbala import hora_bala


@pytest.mark.parametrize('weekday,lord', list(enumerate([
    Planet.MOON, Planet.MARS, Planet.MERCURY, Planet.JUPITER,
    Planet.VENUS, Planet.SATURN, Planet.SUN,
])))
def test_first_hora_belongs_to_local_sunrise_weekday(weekday, lord):
    rise = datetime(2024, 1, 1, 6) + timedelta(days=weekday)
    selected = hora_interval(rise, rise, rise + timedelta(hours=12), rise + timedelta(days=1), weekday)
    assert (selected.lord, selected.index, selected.phase) == (lord, 1, 'Day')


def test_hora_sequence_continues_through_sunset_and_midnight():
    rise = datetime(2024, 1, 7, 6)
    sequence = [Planet.SUN, Planet.VENUS, Planet.MERCURY, Planet.MOON,
                Planet.SATURN, Planet.JUPITER, Planet.MARS]
    for hour in range(24):
        instant = rise + timedelta(hours=hour, minutes=30)
        selected = hora_interval(instant, rise, rise + timedelta(hours=12), rise + timedelta(days=1), 6)
        assert selected.lord == sequence[hour % 7]
        assert selected.index == hour + 1
        assert selected.phase == ('Day' if hour < 12 else 'Night')
        assert selected.start <= instant < selected.end
        assert hora_bala(selected.lord, instant, rise, rise + timedelta(hours=12), rise + timedelta(days=1), 6) == 60


def test_unequal_day_and_night_use_their_own_twelfth():
    rise = datetime(2024, 1, 7, 6)
    sunset, next_rise = rise + timedelta(hours=15), rise + timedelta(days=1)
    day = hora_interval(rise + timedelta(hours=1), rise, sunset, next_rise, 6)
    night = hora_interval(sunset, rise, sunset, next_rise, 6)
    assert day.end - day.start == timedelta(minutes=75)
    assert night.end - night.start == timedelta(minutes=45)
    assert (night.index, night.lord, night.phase) == (13, Planet.JUPITER, 'Night')


def test_exact_fractional_boundary_starts_new_hora():
    rise = datetime(2024, 1, 7, 6)
    sunset = datetime(2024, 1, 7, 21, 0, 1)
    next_rise = rise + timedelta(days=1)
    boundary = datetime(2024, 1, 7, 7, 15, 0, 83333)
    previous = hora_interval(boundary - timedelta(microseconds=1), rise, sunset, next_rise, 6)
    current = hora_interval(boundary, rise, sunset, next_rise, 6)
    assert (previous.index, previous.lord) == (1, Planet.SUN)
    assert (current.index, current.lord) == (2, Planet.VENUS)
    assert previous.end == current.start == boundary


def test_next_sunrise_is_excluded_from_previous_sequence():
    rise = datetime(2024, 1, 7, 6)
    with pytest.raises(ValueError):
        hora_interval(rise + timedelta(days=1), rise, rise + timedelta(hours=12), rise + timedelta(days=1), 6)


def test_before_sunrise_uses_previous_local_weekday_and_birth_offset(monkeypatch):
    offset = timedelta(hours=5.5)
    rise = datetime(2024, 1, 7, 6) - offset
    monkeypatch.setattr('vedic_astro.hora.sunrise_sunset', lambda *args: (
        rise, rise + timedelta(hours=12), rise + timedelta(days=1)))
    birth = BirthData(birth_date=date(2024, 1, 8), birth_time=time(5), latitude=17, longitude=81, utc_offset_hours=5.5)
    result = compute_panchanga(0, 0, birth.birth_date, birth_data=birth)
    assert result.vara == 'Somavara'
    hora = result.hora
    assert hora is not None
    assert hora.sunrise_day_lord == Planet.SUN
    assert (hora.lord, hora.index, hora.phase) == (Planet.MERCURY, 24, 'Night')
    assert hora.start == birth.local_datetime
    assert hora.end == datetime(2024, 1, 8, 6)
    assert hora.sunrise == datetime(2024, 1, 7, 6)


def test_real_birth_hora_matches_hora_bala():
    birth = BirthData(birth_date=date(1998, 9, 4), birth_time=time(0, 3),
                      latitude=17.00517, longitude=81.77784, utc_offset_hours=5.5)
    hora = compute_birth_hora(birth)
    assert (hora.lord, hora.index, hora.phase) == (Planet.MERCURY, 19, 'Night')
    assert hora.start <= birth.local_datetime < hora.end
    assert hora.sunrise.date() == date(1998, 9, 3)
    assert hora.sunrise_day_lord == Planet.JUPITER
    offset = timedelta(hours=birth.utc_offset_hours)
    scores = {planet: hora_bala(planet, birth.utc_datetime, hora.sunrise - offset,
        hora.sunset - offset, hora.next_sunrise - offset, hora.sunrise.weekday())
        for planet in (Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY, Planet.JUPITER, Planet.VENUS, Planet.SATURN)}
    assert scores[hora.lord] == 60
    assert sum(scores.values()) == 60
