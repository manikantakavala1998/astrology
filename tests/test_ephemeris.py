from datetime import datetime

import pytest

from vedic_astro.ephemeris import ascendant_longitude, house_cusps, julian_day_ut, planet_positions
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
