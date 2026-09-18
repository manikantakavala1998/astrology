from vedic_astro.models import Planet, Sign
from vedic_astro.planetary_relations import (
    NATURAL_ENEMIES,
    NATURAL_FRIENDS,
    natural_relation,
    panchadha_relation,
    temporal_relation,
)


def test_natural_relation_is_same_for_identical_planets() -> None:
    assert natural_relation(Planet.SUN, Planet.SUN) == "same"


def test_natural_relation_matches_the_bphs_table() -> None:
    assert natural_relation(Planet.SUN, Planet.MOON) == "friend"
    assert natural_relation(Planet.SUN, Planet.SATURN) == "enemy"
    assert natural_relation(Planet.SUN, Planet.MERCURY) == "neutral"


def test_every_planet_has_a_friend_and_enemy_entry() -> None:
    for planet in Planet:
        if planet in (Planet.RAHU, Planet.KETU):
            continue
        assert planet in NATURAL_FRIENDS
        assert planet in NATURAL_ENEMIES


def test_temporal_relation_friend_houses() -> None:
    # Aries as subject: houses 2/3/4/10/11/12 from Aries are Taurus, Gemini,
    # Cancer, Capricorn, Aquarius, Pisces - all temporal friends.
    for friend_sign in [Sign.TAURUS, Sign.GEMINI, Sign.CANCER, Sign.CAPRICORN, Sign.AQUARIUS, Sign.PISCES]:
        assert temporal_relation(Sign.ARIES, friend_sign) == "friend"


def test_temporal_relation_enemy_houses() -> None:
    # Houses 1/5/6/7/8/9 from Aries: Aries, Leo, Virgo, Libra, Scorpio, Sagittarius.
    for enemy_sign in [Sign.ARIES, Sign.LEO, Sign.VIRGO, Sign.LIBRA, Sign.SCORPIO, Sign.SAGITTARIUS]:
        assert temporal_relation(Sign.ARIES, enemy_sign) == "enemy"


def test_panchadha_relation_own_when_same_planet() -> None:
    assert panchadha_relation(Planet.SUN, Sign.LEO, Planet.SUN, Sign.LEO) == "own"


def test_panchadha_relation_great_friend_when_natural_and_temporal_friend() -> None:
    # Sun (subject, in Aries) and Moon (natural friend of Sun) placed in
    # Taurus - house 2 from Aries, a temporal-friend house.
    assert panchadha_relation(Planet.SUN, Sign.ARIES, Planet.MOON, Sign.TAURUS) == "great_friend"


def test_panchadha_relation_neutral_when_natural_friend_but_temporal_enemy() -> None:
    # Moon is a natural friend of Sun, but placed in Leo (house 1 from
    # Aries, a temporal-enemy house) it should downgrade to neutral.
    assert panchadha_relation(Planet.SUN, Sign.ARIES, Planet.MOON, Sign.LEO) == "neutral"


def test_panchadha_relation_great_enemy_when_natural_and_temporal_enemy() -> None:
    # Saturn is a natural enemy of Sun; placed in Leo (house 1 from Aries,
    # temporal-enemy house) it should be a great enemy.
    assert panchadha_relation(Planet.SUN, Sign.ARIES, Planet.SATURN, Sign.LEO) == "great_enemy"


def test_panchadha_relation_friend_when_natural_neutral_but_temporal_friend() -> None:
    # Mercury is natural-neutral to Sun; placed in Taurus (temporal friend
    # house from Aries) it should be a plain friend.
    assert panchadha_relation(Planet.SUN, Sign.ARIES, Planet.MERCURY, Sign.TAURUS) == "friend"


def test_panchadha_relation_enemy_when_natural_neutral_but_temporal_enemy() -> None:
    assert panchadha_relation(Planet.SUN, Sign.ARIES, Planet.MERCURY, Sign.LEO) == "enemy"
