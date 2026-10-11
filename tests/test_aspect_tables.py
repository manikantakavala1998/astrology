import pytest

from vedic_astro.aspect_tables import build_aspect_tables
from vedic_astro.models import SIGNS_IN_ORDER, NakshatraPlacement, Planet, PlanetPosition


def position(planet: Planet, longitude: float, house: int = 1) -> PlanetPosition:
    return PlanetPosition(
        planet=planet, longitude=longitude, sign=SIGNS_IN_ORDER[int(longitude // 30)],
        degree_in_sign=longitude % 30, house=house, retrograde=planet == Planet.SATURN,
        nakshatra=NakshatraPlacement(name="Ashwini", index=1, pada=1, lord=Planet.KETU),
    )


def natal_positions() -> list[PlanetPosition]:
    # Independent known placements: 4 September 1998, 00:03 IST, Rajahmundry.
    return [position(p, longitude) for p, longitude in (
        (Planet.SUN, 137.2172), (Planet.MOON, 281.3945), (Planet.MARS, 105.1056),
        (Planet.MERCURY, 119.6699), (Planet.JUPITER, 330.8331), (Planet.VENUS, 122.4153),
        (Planet.SATURN, 9.4792), (Planet.RAHU, 126.8741), (Planet.KETU, 306.8741),
    )]


def test_known_natal_aspects_use_signs_even_when_house_positions_are_all_one() -> None:
    rows = {row["planet"]: row for row in build_aspect_tables(natal_positions())["vedic"]}
    expected = {
        "Sun": [("Ketu", 7)], "Moon": [("Mars", 7), ("Mercury", 7)],
        "Mars": [("Moon", 7), ("Ketu", 8)], "Mercury": [("Moon", 7)],
        "Jupiter": [("Mars", 5), ("Mercury", 5)], "Venus": [("Ketu", 7)],
        "Saturn": [("Moon", 10)], "Rahu": [], "Ketu": [],
    }
    assert {name: [(link["target_planet"], link["aspect_number"]) for link in row["aspects"]]
            for name, row in rows.items()} == expected
    assert rows["Saturn"]["retrograde"] is True
    assert rows["Sun"]["sign"] == "Leo"
    assert [(link["target_planet"], link["target_sign"]) for link in rows["Moon"]["aspects"]] == [
        ("Mars", "Cancer"), ("Mercury", "Cancer"),
    ]
    assert rows["Sun"]["aspects"][0]["target_sign"] == "Aquarius"


def test_aspected_signs_include_empty_signs_and_wrap_around_zodiac() -> None:
    rows = {row["planet"]: row for row in build_aspect_tables(natal_positions())["vedic"]}
    assert rows["Jupiter"]["aspected_signs"] == [
        {"sign": "Cancer", "aspect_number": 5},
        {"sign": "Virgo", "aspect_number": 7},
        {"sign": "Scorpio", "aspect_number": 9},
    ]
    assert rows["Mars"]["aspected_signs"] == [
        {"sign": "Libra", "aspect_number": 4},
        {"sign": "Capricorn", "aspect_number": 7},
        {"sign": "Aquarius", "aspect_number": 8},
    ]
    assert rows["Rahu"]["aspected_signs"] == []
    assert rows["Ketu"]["aspected_signs"] == []


def test_house_system_and_input_order_do_not_change_sign_based_connections() -> None:
    planets = natal_positions()
    expected = build_aspect_tables(planets)
    for index, planet in enumerate(planets):
        planet.house = index + 2
    assert build_aspect_tables(planets) == expected
    shuffled = build_aspect_tables(list(reversed(planets)))
    for method in ("vedic", "western"):
        actual = {row["planet"]: row for row in shuffled[method]}
        for row in expected[method]:
            assert sorted(actual[row["planet"]]["aspects"], key=lambda link: link["target_planet"]) == sorted(row["aspects"], key=lambda link: link["target_planet"])


@pytest.mark.parametrize("angle,name", [(0, "Conjunction"), (60, "Sextile"), (90, "Square"), (120, "Trine"), (180, "Opposition")])
def test_exact_western_major_aspects_are_mutual(angle: int, name: str) -> None:
    rows = build_aspect_tables([position(Planet.SUN, 15), position(Planet.MOON, 15 + angle)])["western"]
    for row, target in zip(rows, ("Moon", "Sun")):
        assert len(row["aspects"]) == 1
        link = row["aspects"][0]
        assert link["target_planet"] == target
        assert link["aspect_name"] == name
        assert link["exact_angle"] == angle
        assert link["orb"] == 0


def test_western_conjunction_crosses_zero_degrees_without_self_aspects() -> None:
    rows = build_aspect_tables([position(Planet.SUN, 359), position(Planet.MOON, 1)])["western"]
    assert rows[0]["aspects"][0] == {
        "target_planet": "Moon", "target_sign": "Aries", "aspect_name": "Conjunction",
        "exact_angle": 0, "separation": 2, "orb": 2,
    }
    assert len(rows[0]["aspects"]) == 1


@pytest.mark.parametrize("longitude,included", [(100, True), (100.000001, False)])
def test_western_ten_degree_candidate_boundary(longitude: float, included: bool) -> None:
    rows = build_aspect_tables([position(Planet.SUN, 0), position(Planet.MOON, longitude)])["western"]
    assert bool(rows[0]["aspects"]) is included


def test_known_natal_western_angles_and_target_signs() -> None:
    rows = {row["planet"]: row for row in build_aspect_tables(natal_positions())["western"]}
    links = {link["target_planet"]: link for link in rows["Moon"]["aspects"]}
    assert links["Mars"]["aspect_name"] == "Opposition"
    assert links["Mars"]["orb"] == pytest.approx(3.7111)
    assert links["Mars"]["target_sign"] == "Cancer"
    # A close conjunction can cross a sign boundary in the Western table.
    venus = next(link for link in rows["Mercury"]["aspects"] if link["target_planet"] == "Venus")
    assert venus["aspect_name"] == "Conjunction"
    assert venus["target_sign"] == "Leo"
    assert venus["orb"] == pytest.approx(2.7454)
    ketu = next(link for link in rows["Rahu"]["aspects"] if link["target_planet"] == "Ketu")
    assert ketu["orb"] == pytest.approx(0)


def test_empty_input_and_planets_without_targets_still_have_well_formed_rows() -> None:
    assert build_aspect_tables([])["vedic"] == []
    report = build_aspect_tables([position(Planet.JUPITER, 340)])
    assert report["western"][0]["aspects"] == []
    assert report["vedic"][0]["aspects"] == []
    assert len(report["vedic"][0]["aspected_signs"]) == 3
