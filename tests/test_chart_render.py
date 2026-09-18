from datetime import date, time

from vedic_astro.chart import build_kundali_chart
from vedic_astro.chart_render import (
    SOUTH_INDIAN_GRID,
    ashtakavarga_mini_grid,
    bhava_chalit_layout,
    navamsa_layout,
    south_indian_layout,
    varga_layout,
)
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
    assert "Su" in [label.code for label in sun_cell.planet_labels]


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
    assert "Su" in [label.code for label in sun_cell.planet_labels]


def test_varga_layout_matches_south_indian_layout_for_d1() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    assert varga_layout(chart, "D1") == south_indian_layout(chart)


def test_varga_layout_marks_the_chart_specific_ascendant_as_house_one() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = varga_layout(chart, "D10")
    ascendant_cells = [
        cell for row in grid for cell in row if cell is not None and cell.is_ascendant
    ]
    assert len(ascendant_cells) == 1
    assert ascendant_cells[0].sign == chart.ascendant.varga_signs["D10"]
    assert ascendant_cells[0].house == 1


def test_varga_layout_places_planets_by_their_own_varga_sign() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = varga_layout(chart, "D3")
    sun = next(p for p in chart.planets if p.planet.value == "Sun")
    sun_d3_sign = sun.varga_signs["D3"]
    sun_cell = next(
        cell for row in grid for cell in row if cell is not None and cell.sign == sun_d3_sign
    )
    assert "Su" in [label.code for label in sun_cell.planet_labels]


def test_bhava_chalit_layout_places_planets_by_d1_sign() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = bhava_chalit_layout(chart)
    sun = next(p for p in chart.planets if p.planet.value == "Sun")
    sun_cell = next(
        cell for row in grid for cell in row if cell is not None and cell.sign == sun.sign
    )
    assert "Su" in [label.code for label in sun_cell.planet_labels]


def test_bhava_chalit_layout_has_exactly_one_house_one_cell() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = bhava_chalit_layout(chart)
    house_one_cells = [cell for row in grid for cell in row if cell is not None and cell.house == 1]
    assert len(house_one_cells) == 1
    assert house_one_cells[0].is_ascendant


def test_bhava_chalit_layout_covers_all_twelve_houses_exactly_once() -> None:
    # True for this moderate-latitude fixture, but not a guaranteed property
    # of Placidus cusps in general - at extreme latitudes, house spans can
    # be uneven enough that a house catches zero or two sign-midpoints. This
    # is a regression check for the sample data, not a universal invariant.
    chart = build_kundali_chart(_sample_birth_data())
    grid = bhava_chalit_layout(chart)
    houses = sorted(cell.house for row in grid for cell in row if cell is not None)
    assert houses == list(range(1, 13))


def test_planet_labels_carry_dignity_suffix_and_color_class() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = south_indian_layout(chart)
    saturn = next(p for p in chart.planets if p.planet.value == "Saturn")
    saturn_cell = next(
        cell for row in grid for cell in row if cell is not None and cell.sign == saturn.sign
    )
    saturn_label = next(label for label in saturn_cell.planet_labels if label.code == "Sa")
    assert saturn_label.color_class == "planet-color-saturn"
    # Saturn is Own Sign in this fixture (Capricorn), not Exalted/Debilitated.
    assert saturn_label.dignity_suffix == ""


def test_chart_cells_carry_direction_and_element() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    grid = south_indian_layout(chart)
    aries_cell = next(
        cell for row in grid for cell in row if cell is not None and cell.sign == Sign.ARIES
    )
    assert aries_cell.direction == "E"
    assert aries_cell.element_symbol


def _dummy_band(value: int) -> tuple[str, str]:
    return ("weak", "Weak") if value < 4 else ("strong", "Strong")


def test_ashtakavarga_mini_grid_shows_bindus_and_natal_occupation() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    assert chart.ashtakavarga is not None
    natal_signs = {p.sign for p in chart.planets}
    grid = ashtakavarga_mini_grid(chart.ashtakavarga.sav, natal_signs, _dummy_band)
    cells = [cell for row in grid for cell in row if cell is not None]
    assert len(cells) == 12
    assert sum(cell.bindus for cell in cells) == 337
    for cell in cells:
        assert cell.is_natal_occupied == (cell.sign in natal_signs)


def test_ashtakavarga_mini_grid_applies_the_given_band_function() -> None:
    chart = build_kundali_chart(_sample_birth_data())
    assert chart.ashtakavarga is not None
    natal_signs = {p.sign for p in chart.planets}
    grid = ashtakavarga_mini_grid(chart.ashtakavarga.sav, natal_signs, _dummy_band)
    cells = [cell for row in grid for cell in row if cell is not None]
    for cell in cells:
        expected_class, expected_label = _dummy_band(cell.bindus)
        assert cell.band_class == expected_class
        assert cell.band_label == expected_label
