from vedic_astro.models import Sign
from vedic_astro.sign_attributes import SIGN_DIRECTION, SIGN_ELEMENT_NAME, SIGN_ELEMENT_SYMBOL


def test_every_sign_has_a_direction_and_element() -> None:
    for sign in Sign:
        assert sign in SIGN_DIRECTION
        assert sign in SIGN_ELEMENT_SYMBOL
        assert sign in SIGN_ELEMENT_NAME


def test_directions_and_elements_match_the_users_exact_table() -> None:
    expected = {
        Sign.ARIES: ("E", "Fire"),
        Sign.TAURUS: ("S", "Earth"),
        Sign.GEMINI: ("W", "Air"),
        Sign.CANCER: ("N", "Water"),
        Sign.LEO: ("E", "Fire"),
        Sign.VIRGO: ("S", "Earth"),
        Sign.LIBRA: ("W", "Air"),
        Sign.SCORPIO: ("N", "Water"),
        Sign.SAGITTARIUS: ("E", "Fire"),
        Sign.CAPRICORN: ("S", "Earth"),
        Sign.AQUARIUS: ("W", "Air"),
        Sign.PISCES: ("N", "Water"),
    }
    for sign, (direction, element) in expected.items():
        assert SIGN_DIRECTION[sign] == direction
        assert SIGN_ELEMENT_NAME[sign] == element
