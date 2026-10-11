"""Classical examples, parity, unequal D30 spans and composite carry-over."""
import pytest

from vedic_astro.amsa_rulers import amsa_ruler
from vedic_astro.divisional_charts import VARGA_REGISTRY, chaturvimsamsa_sign, shashtiamsa_sign
from vedic_astro.models import Sign


@pytest.mark.parametrize("code,longitude,deity,part", [
    ("D2", 0, "Surya (Sun)", 1), ("D2", 15, "Chandra (Moon)", 2),
    ("D2", 30, "Chandra (Moon)", 1), ("D2", 45, "Surya (Sun)", 2),
    ("D3", 9.999, "Narada", 1), ("D3", 10, "Agastya", 2), ("D3", 20, "Durvasa", 3),
    ("D4", 15, "Sanatkumara", 3), ("D4", 22.5, "Sanatana", 4),
    ("D7", 0, "Kshara", 1), ("D7", 30, "Shuddha Jala", 1),
    ("D9", 0, "Deva", 1), ("D9", 30, "Manushya", 1), ("D9", 60, "Rakshasa", 1),
    ("D9", 63.34, "Manushya", 2),
    ("D10", 0, "Indra", 1), ("D10", 30, "Ananta", 1),
    ("D12", 0, "Ganesha", 1), ("D12", 2.5, "Ashvini Kumara", 2),
    ("D12", 5, "Yama", 3), ("D12", 7.5, "Sarpa", 4), ("D12", 10, "Ganesha", 5),
    ("D12", 30, "Ganesha", 1), ("D12", 57.5, "Sarpa", 12),
    ("D16", 0, "Brahma", 1), ("D16", 30, "Surya", 1),
    ("D20", 0, "Kali", 1), ("D20", 30, "Daya", 1), ("D20", 33, "Chinnashirsha", 3),
    ("D20", 28.5, "Sumukhi", 20), ("D20", 58.5, "Aparajita", 20),
    ("D24", 0, "Skanda", 1), ("D24", 30, "Bhima", 1),
    ("D27", 0, "Ashvini Kumara", 1), ("D27", 30, "Pushan", 1),
    ("D40", 0, "Vishnu", 1), ("D40", 30, "Vishnu", 1), ("D40", 3, "Dhata", 5),
    ("D45", 0, "Brahma", 1), ("D45", 30, "Shiva", 1), ("D45", 60, "Vishnu", 1),
    ("D60", 0, "Ghora", 1), ("D60", .5, "Rakshasa", 2),
    ("D60", 29.5, "Chandrarekha", 60), ("D60", 30, "Chandrarekha", 1),
    ("D60", 59.5, "Ghora", 60),
])
def test_classical_names_and_exact_boundaries(code, longitude, deity, part):
    ruler = amsa_ruler(longitude, code)
    assert ruler.deity == deity and ruler.part == part
    assert ruler.status == "defined" and ruler.reference.startswith("BPHS 6.")


@pytest.mark.parametrize("longitude,deity,part,lower,upper", [
    (0, "Agni", 1, 0, 5), (5, "Vayu", 2, 5, 10),
    (10, "Indra", 3, 10, 18), (18, "Kubera", 4, 18, 25), (25, "Varuna", 5, 25, 30),
    (30, "Varuna", 1, 0, 5), (35, "Kubera", 2, 5, 12),
    (42, "Indra", 3, 12, 20), (50, "Vayu", 4, 20, 25), (55, "Agni", 5, 25, 30),
    (59.9999999995, "Agni", 5, 25, 30),
])
def test_d30_uses_five_unequal_segments(longitude, deity, part, lower, upper):
    ruler = amsa_ruler(longitude, "D30")
    assert (ruler.deity, ruler.part, ruler.start_degree, ruler.end_degree) == (deity, part, lower, upper)
    assert ruler.divisions == 5


def test_even_deity_reversal_does_not_change_sign_mapping():
    assert amsa_ruler(30, "D24").deity == "Bhima"
    assert chaturvimsamsa_sign(30) == Sign.CANCER
    assert amsa_ruler(30, "D60").deity == "Chandrarekha"
    assert shashtiamsa_sign(30) == Sign.ARIES


@pytest.mark.parametrize("code,longitude,text", [
    ("D81", 0, "D9: Deva → D9: Deva"),
    ("D81", 30, "D9: Manushya → D9: Deva"),  # Taurus -> Capricorn, a movable intermediate sign
    ("D108", 0, "D9: Deva → D12: Ganesha"),
    ("D108", 30 / 108, "D9: Deva → D12: Ashvini Kumara"),
    ("D144", 0, "D12: Ganesha → D12: Ganesha"),
    ("D144", 2.5, "D12: Ashvini Kumara → D12: Ganesha"),
])
def test_composites_label_component_deities(code, longitude, text):
    result = amsa_ruler(longitude, code)
    assert result.deity == text
    assert result.status == "composite" and "Component rules" in result.reference


@pytest.mark.parametrize("code", [spec.code for spec in VARGA_REGISTRY])
def test_every_available_chart_wraps_longitudes_and_stays_in_range(code):
    assert amsa_ruler(360, code) == amsa_ruler(0, code)
    for longitude in (0, 12.34, 30, 71.5, 359.9999999995):
        ruler = amsa_ruler(longitude, code)
        assert 1 <= ruler.part <= ruler.divisions
        assert 0 <= ruler.start_degree < ruler.end_degree <= 30


def test_unsupported_deities_are_explicit_instead_of_borrowing_another_division():
    assert amsa_ruler(15, "D1").status == "not_applicable"
    for code in ("D5", "D6", "D8", "D11"):
        ruler = amsa_ruler(15, code)
        assert ruler.status == "unconfirmed" and ruler.deity is None
    with pytest.raises(ValueError, match="Unknown"):
        amsa_ruler(15, "D13")
