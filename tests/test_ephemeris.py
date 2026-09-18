from datetime import datetime

import pytest

from vedic_astro.ephemeris import (
    ascendant_longitude,
    declination_degrees,
    house_cusps,
    julian_day_ut,
    mean_obliquity_degrees,
    planet_positions,
    sunrise_sunset,
)
from vedic_astro.models import HouseSystem, NodeType, Planet


def test_julian_day_matches_known_epoch() -> None:
    # J2000.0 epoch: 2000-01-01 12:00 UT -> JD 2451545.0 exactly.
    assert julian_day_ut(datetime(2000, 1, 1, 12, 0, 0)) == pytest.approx(2451545.0)


def test_planet_positions_returns_all_nine_grahas() -> None:
    positions = planet_positions(datetime(2000, 1, 1, 12, 0, 0), "lahiri", NodeType.MEAN)
    assert set(positions) == {
        Planet.SUN,
        Planet.MOON,
        Planet.MARS,
        Planet.MERCURY,
        Planet.JUPITER,
        Planet.VENUS,
        Planet.SATURN,
        Planet.RAHU,
        Planet.KETU,
    }
    for pos in positions.values():
        assert 0 <= pos.longitude < 360


def test_sun_sidereal_longitude_matches_known_lahiri_value() -> None:
    # Published Lahiri-ayanamsha sidereal Sun longitude for 2000-01-01 12:00 UT
    # is ~256.5 degrees (tropical ~280.3 minus ayanamsha ~23.85).
    positions = planet_positions(datetime(2000, 1, 1, 12, 0, 0), "lahiri", NodeType.MEAN)
    assert positions[Planet.SUN].longitude == pytest.approx(256.5, abs=0.1)


def test_rahu_and_ketu_are_always_opposite() -> None:
    positions = planet_positions(datetime(2000, 1, 1, 12, 0, 0), "lahiri", NodeType.MEAN)
    rahu = positions[Planet.RAHU].longitude
    ketu = positions[Planet.KETU].longitude
    assert (rahu + 180) % 360 == pytest.approx(ketu, abs=1e-9)


def test_ascendant_longitude_in_valid_range() -> None:
    asc = ascendant_longitude(datetime(2000, 1, 1, 12, 0, 0), 28.6139, 77.2090, "lahiri")
    assert 0 <= asc < 360


def test_unsupported_ayanamsha_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported ayanamsha"):
        planet_positions(datetime(2000, 1, 1, 12, 0, 0), "not-a-real-one", NodeType.MEAN)


def test_house_cusps_returns_twelve_valid_longitudes() -> None:
    cusps = house_cusps(datetime(2000, 1, 1, 12, 0, 0), 13.0827, 80.2707, "lahiri", HouseSystem.PLACIDUS)
    assert len(cusps) == 12
    assert all(0 <= c < 360 for c in cusps)


def test_house_cusps_first_cusp_matches_ascendant() -> None:
    # The 1st house cusp is always the Ascendant itself, regardless of system.
    asc = ascendant_longitude(datetime(2000, 1, 1, 12, 0, 0), 13.0827, 80.2707, "lahiri")
    for system in HouseSystem:
        if system == HouseSystem.WHOLE_SIGN:
            continue  # whole-sign cusps start at the sign boundary, not the exact ascendant
        cusps = house_cusps(datetime(2000, 1, 1, 12, 0, 0), 13.0827, 80.2707, "lahiri", system)
        assert cusps[0] == pytest.approx(asc, abs=0.01)


def test_house_cusps_different_systems_give_different_cusps() -> None:
    equal = house_cusps(datetime(2000, 1, 1, 12, 0, 0), 13.0827, 80.2707, "lahiri", HouseSystem.EQUAL)
    placidus = house_cusps(datetime(2000, 1, 1, 12, 0, 0), 13.0827, 80.2707, "lahiri", HouseSystem.PLACIDUS)
    porphyry = house_cusps(datetime(2000, 1, 1, 12, 0, 0), 13.0827, 80.2707, "lahiri", HouseSystem.PORPHYRY)
    # 2nd cusp onward should differ between systems (1st/Ascendant is shared).
    assert equal[1] != pytest.approx(placidus[1])
    assert placidus[1] != pytest.approx(porphyry[1])


def test_house_cusps_equal_system_is_evenly_spaced() -> None:
    cusps = house_cusps(datetime(2000, 1, 1, 12, 0, 0), 13.0827, 80.2707, "lahiri", HouseSystem.EQUAL)
    for i in range(12):
        expected = (cusps[0] + 30 * i) % 360
        assert cusps[i] == pytest.approx(expected, abs=0.01)


def test_sunrise_sunset_brackets_the_given_moment() -> None:
    for hour in [0.0, 0.2, 6.0, 12.0, 18.0, 23.99]:
        dt = datetime(2024, 6, 15, int(hour), int((hour % 1) * 60))
        sunrise, sunset, next_sunrise = sunrise_sunset(dt, 13.0827, 80.2707)
        assert sunrise <= dt < next_sunrise
        assert sunrise < sunset < next_sunrise


def test_sunrise_sunset_returns_naive_datetimes() -> None:
    # Matches this codebase's convention (implicit UTC, no tzinfo) - see
    # BirthData.utc_datetime and TransitSegment.
    sunrise, sunset, next_sunrise = sunrise_sunset(datetime(2024, 6, 15, 6, 0, 0), 13.0827, 80.2707)
    assert sunrise.tzinfo is None
    assert sunset.tzinfo is None
    assert next_sunrise.tzinfo is None


def test_mean_obliquity_is_close_to_the_known_modern_value() -> None:
    obliquity = mean_obliquity_degrees(datetime(2024, 6, 15, 6, 0, 0))
    assert obliquity == pytest.approx(23.44, abs=0.02)


def test_declination_matches_zero_at_an_equinox_point() -> None:
    # A body at 0 degrees tropical longitude (the vernal equinox point)
    # with zero ecliptic latitude always has zero declination, regardless
    # of obliquity.
    assert declination_degrees(0.0, 0.0, 23.44) == pytest.approx(0.0, abs=1e-9)


def test_declination_matches_obliquity_at_the_summer_solstice_point() -> None:
    # A body at 90 degrees tropical longitude (summer solstice point) with
    # zero ecliptic latitude has declination exactly equal to the obliquity.
    assert declination_degrees(90.0, 0.0, 23.44) == pytest.approx(23.44, abs=1e-6)


def test_sun_declination_is_near_maximum_just_before_june_solstice() -> None:
    dt = datetime(2024, 6, 15, 6, 0, 0)
    positions = planet_positions(dt, "lahiri", NodeType.MEAN)
    sun = positions[Planet.SUN]
    obliquity = mean_obliquity_degrees(dt)
    # Reconstruct the Sun's tropical longitude directly via the ayanamsha
    # offset baked into planet_positions (sidereal = tropical - ayanamsha).
    import swisseph as swe

    from vedic_astro.ephemeris import configure_ayanamsha, julian_day_ut

    configure_ayanamsha("lahiri")
    ayanamsha_value = swe.get_ayanamsa_ut(julian_day_ut(dt))
    tropical_longitude = (sun.longitude + ayanamsha_value) % 360
    declination = declination_degrees(tropical_longitude, sun.latitude, obliquity)
    assert declination == pytest.approx(23.4, abs=0.3)
