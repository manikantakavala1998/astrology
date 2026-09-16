from datetime import date, time

from vedic_astro.chart import build_kundali_chart
from vedic_astro.chart_render import SOUTH_INDIAN_GRID, navamsa_layout, south_indian_layout
from vedic_astro.models import BirthData, Sign
from vedic_astro.varga import navamsa_sign


def _sample_birth_data() -> BirthData:
    return BirthData(
        birth_date=date(1990, 6, 15),
        birth_time=time(8, 30, 0),
        latitude=13.0827,
        longitude=80.2707,
        utc_offset_hours=5.5,
    )


def test_grid_is_four_by_four() -> None:
    assert len(SOUTH_INDIAN_GRID) == 4
    assert all(len(row) == 4 for row in SOUTH_INDIAN_GRID)


def test_center_cells_are_blank() -> None:
    assert SOUTH_INDIAN_GRID[1][1] is None
    assert SOUTH_INDIAN_GRID[1][2] is None
    assert SOUTH_INDIAN_GRID[2][1] is None
    assert SOUTH_INDIAN_GRID[2][2] is None


def test_every_sign_appears_exactly_once() -> None:
    signs = [cell for row in SOUTH_INDIAN_GRID for cell in row if cell is not None]
    assert sorted(signs, key=lambda s: s.value) == sorted(list(Sign), key=lambda s: s.value)


def test_grid_border_is_clockwise_from_aries() -> None:
    # Walking the border starting at Aries should visit all 12 signs in order.
    border = [
        SOUTH_INDIAN_GRID[0][1], SOUTH_INDIAN_GRID[0][2], SOUTH_INDIAN_GRID[0][3],
        SOUTH_INDIAN_GRID[1][3], SOUTH_INDIAN_GRID[2][3], SOUTH_INDIAN_GRID[3][3],
        SOUTH_INDIAN_GRID[3][2], SOUTH_INDIAN_GRID[3][1], SOUTH_INDIAN_GRID[3][0],
        SOUTH_INDIAN_GRID[2][0], SOUTH_INDIAN_GRID[1][0], SOUTH_INDIAN_GRID[0][0],
    ]
    assert border == list(Sign)


def test_south_indian_layout_marks_ascendant_as_house_one() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = south_indian_layout(chart)
    ascendant_cells = [
        cell for row in grid for cell in row if cell is not None and cell.is_ascendant
    ]
    assert len(ascendant_cells) == 1
    assert ascendant_cells[0].sign == chart.ascendant.sign
    assert ascendant_cells[0].house == 1


def test_south_indian_layout_places_planets_in_correct_sign_cell() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = south_indian_layout(chart)
    sun = next(p for p in chart.planets if p.planet.value == "Sun")
    sun_cell = next(
        cell for row in grid for cell in row if cell is not None and cell.sign == sun.sign
    )
    assert "Su" in sun_cell.planet_labels


def test_navamsa_layout_marks_d9_ascendant_as_house_one() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = navamsa_layout(chart)
    expected_d9_ascendant = navamsa_sign(chart.ascendant.longitude)
    ascendant_cells = [
        cell for row in grid for cell in row if cell is not None and cell.is_ascendant
    ]
    assert len(ascendant_cells) == 1
    assert ascendant_cells[0].sign == expected_d9_ascendant
    assert ascendant_cells[0].house == 1


def test_navamsa_layout_places_planets_by_d9_sign_not_d1_sign() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = navamsa_layout(chart)
    sun = next(p for p in chart.planets if p.planet.value == "Sun")
    assert sun.navamsa_sign is not None
    sun_cell = next(
        cell for row in grid for cell in row if cell is not None and cell.sign == sun.navamsa_sign
    )
    assert "Su" in sun_cell.planet_labels
