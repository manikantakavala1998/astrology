import pytest

from vedic_astro.divisional_charts import (
    VARGA_REGISTRY,
    dasamsa_sign,
    drekkana_sign,
    dwadasamsa_sign,
    saptamsa_sign,
    trimsamsa_sign,
)
from vedic_astro.models import SIGNS_IN_ORDER, Sign


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # Aries, part 0 -> same sign
        (15.0, Sign.LEO),  # Aries, part 1 -> 5th sign from Aries
        (25.0, Sign.SAGITTARIUS),  # Aries, part 2 -> 9th sign from Aries
        (45.0, Sign.VIRGO),  # Taurus, part 1 -> 5th sign from Taurus
        (55.0, Sign.CAPRICORN),  # Taurus, part 2 -> 9th sign from Taurus
    ],
)
def test_drekkana_sign(longitude: float, expected: Sign) -> None:
    assert drekkana_sign(longitude) == expected


def test_drekkana_wraps_at_360() -> None:
    assert drekkana_sign(360.0) == drekkana_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # Aries (odd), part 0 -> anchor is Aries itself
        (30.0, Sign.SCORPIO),  # Taurus (even), part 0 -> anchor is its 7th (opposite) sign
    ],
)
def test_saptamsa_sign(longitude: float, expected: Sign) -> None:
    assert saptamsa_sign(longitude) == expected


def test_saptamsa_wraps_at_360() -> None:
    assert saptamsa_sign(360.0) == saptamsa_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # Aries (odd), part 0 -> anchor is Aries itself
        (30.0, Sign.CAPRICORN),  # Taurus (even), part 0 -> anchor is its 9th sign
    ],
)
def test_dasamsa_sign(longitude: float, expected: Sign) -> None:
    assert dasamsa_sign(longitude) == expected


def test_dasamsa_wraps_at_360() -> None:
    assert dasamsa_sign(360.0) == dasamsa_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (0.0, Sign.ARIES),  # Aries, part 0 -> same sign
        (2.5, Sign.TAURUS),  # Aries, part 1 -> next sign forward
    ],
)
def test_dwadasamsa_sign(longitude: float, expected: Sign) -> None:
    assert dwadasamsa_sign(longitude) == expected


def test_dwadasamsa_cycles_twelve_times_per_sign() -> None:
    signs_seen = {dwadasamsa_sign(i * 2.5) for i in range(12)}
    assert len(signs_seen) == 12


def test_dwadasamsa_wraps_at_360() -> None:
    assert dwadasamsa_sign(360.0) == dwadasamsa_sign(0.0)


@pytest.mark.parametrize(
    ("longitude", "expected"),
    [
        (2.0, Sign.ARIES),  # Gemini (odd), degree 2 -> Mars segment -> Aries
        (22.0, Sign.GEMINI),  # Gemini (odd), degree 22 -> Mercury segment -> Gemini (own sign)
        (5.0, Sign.AQUARIUS),  # Aries (odd), degree 5 (boundary) -> Saturn segment, not Mars
        (98.0, Sign.VIRGO),  # Cancer (even), degree 8 -> Mercury segment -> Virgo
        (90.0, Sign.TAURUS),  # Cancer (even), degree 0 -> Venus segment -> Taurus
    ],
)
def test_trimsamsa_sign(longitude: float, expected: Sign) -> None:
    assert trimsamsa_sign(longitude) == expected


def test_trimsamsa_wraps_at_360() -> None:
    assert trimsamsa_sign(360.0) == trimsamsa_sign(0.0)


def test_varga_registry_has_all_23_standard_charts() -> None:
    assert len(VARGA_REGISTRY) == 23
    codes = [spec.code for spec in VARGA_REGISTRY]
    assert len(set(codes)) == 23  # no duplicates
    assert codes[0] == "D1"
    assert codes[-1] == "D144"


def test_all_23_varga_charts_are_available_with_documented_methods() -> None:
    for spec in VARGA_REGISTRY:
        assert spec.sign_fn is not None, spec.code
        assert spec.held_reason is None, spec.code
        assert spec.method, spec.code


# Independently specified starting-sign tables in Aries-to-Pisces order.
# The offset is the count between consecutive parts, not natal signs.
@pytest.mark.parametrize(("code", "anchors", "step"), [
    ("D4", (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), 3),
    ("D6", (0, 6, 0, 6, 0, 6, 0, 6, 0, 6, 0, 6), 1),
    ("D8", (0, 8, 4, 0, 8, 4, 0, 8, 4, 0, 8, 4), 1),
    ("D11", (0, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1), 1),
    ("D16", (0, 4, 8, 0, 4, 8, 0, 4, 8, 0, 4, 8), 1),
    ("D20", (0, 8, 4, 0, 8, 4, 0, 8, 4, 0, 8, 4), 1),
    ("D24", (4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3), 1),
    ("D27", (0, 3, 6, 9, 0, 3, 6, 9, 0, 3, 6, 9), 1),
    ("D40", (0, 6, 0, 6, 0, 6, 0, 6, 0, 6, 0, 6), 1),
    ("D45", (0, 4, 8, 0, 4, 8, 0, 4, 8, 0, 4, 8), 1),
    ("D60", (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), 1),
    ("D81", (0, 9, 6, 3, 0, 9, 6, 3, 0, 9, 6, 3), 1),
])
def test_new_equal_divisions_all_signs_and_every_boundary(code, anchors, step) -> None:
    spec = next(spec for spec in VARGA_REGISTRY if spec.code == code)
    assert spec.sign_fn is not None
    for natal_index, anchor in enumerate(anchors):
        for part in range(spec.divisions):
            boundary = natal_index * 30 + part * 30 / spec.divisions
            expected = SIGNS_IN_ORDER[(anchor + step * part) % 12]
            assert spec.sign_fn(boundary) == expected, (code, natal_index, part)
            assert spec.sign_fn(boundary + 0.1 * 30 / spec.divisions) == expected
            if part:
                previous = SIGNS_IN_ORDER[(anchor + step * (part - 1)) % 12]
                assert spec.sign_fn(boundary - 1e-7) == previous
        assert spec.sign_fn(natal_index * 30 + 29.9999999) == SIGNS_IN_ORDER[
            (anchor + step * (spec.divisions - 1)) % 12
        ]


def test_panchamsa_uses_equal_parts_and_both_parity_sequences() -> None:
    spec = next(spec for spec in VARGA_REGISTRY if spec.code == "D5")
    assert spec.sign_fn is not None
    for natal in range(12):
        expected = (Sign.ARIES, Sign.AQUARIUS, Sign.SAGITTARIUS, Sign.GEMINI, Sign.LIBRA) if natal % 2 == 0 else (
            Sign.TAURUS, Sign.VIRGO, Sign.PISCES, Sign.CAPRICORN, Sign.SCORPIO,
        )
        for part, sign in enumerate(expected):
            assert spec.sign_fn(natal * 30 + part * 6) == sign
            assert spec.sign_fn(natal * 30 + part * 6 + 5.9999999) == sign


@pytest.mark.parametrize(("code", "longitude", "expected"), [
    ("D60", 135.25, Sign.LIBRA),  # 15.25° in Leo: part 30, Aries + 30.
    ("D81", 31.0, Sign.PISCES),  # D9 Capricorn 9° -> D9 Pisces.
    ("D81", 34.0, Sign.SCORPIO),  # D9 Aquarius 6° -> D9 Scorpio.
    ("D108", 31.0, Sign.ARIES),  # D9 Capricorn 9° -> D12 Aries.
    ("D108", 34.0, Sign.ARIES),  # D9 Aquarius 6° -> D12 Aries.
    ("D108", 10.0 / 3, Sign.TAURUS),  # First new Navamsa, first D12 part.
    ("D144", 31.0, Sign.VIRGO),  # D12 Taurus 12° -> D12 Virgo.
    ("D144", 2.5, Sign.TAURUS),  # D12 Taurus 0° -> D12 Taurus.
])
def test_degree_only_and_composite_worked_examples(code, longitude, expected) -> None:
    spec = next(spec for spec in VARGA_REGISTRY if spec.code == code)
    assert spec.sign_fn is not None
    assert spec.sign_fn(longitude) == expected


@pytest.mark.parametrize("code", ["D108", "D144"])
def test_composites_match_two_stage_mapping_at_all_subdivision_boundaries(code) -> None:
    spec = next(spec for spec in VARGA_REGISTRY if spec.code == code)
    assert spec.sign_fn is not None
    first_factor = 9 if code == "D108" else 12
    for natal in range(12):
        for first_part in range(first_factor):
            # Independent first-chart starting-sign tables.
            first_sign = ((0, 9, 6, 3, 0, 9, 6, 3, 0, 9, 6, 3)[natal] + first_part) % 12 if code == "D108" else (
                natal + first_part
            ) % 12
            for second_part in range(12):
                boundary = natal * 30 + (first_part * 12 + second_part) * 30 / spec.divisions
                assert spec.sign_fn(boundary) == SIGNS_IN_ORDER[(first_sign + second_part) % 12]
                assert spec.sign_fn(boundary + 1e-7) == SIGNS_IN_ORDER[(first_sign + second_part) % 12]
                if first_part or second_part:
                    previous_first = first_sign if second_part else (first_sign - 1) % 12
                    previous_second = second_part - 1 if second_part else 11
                    assert spec.sign_fn(boundary - 1e-7) == SIGNS_IN_ORDER[
                        (previous_first + previous_second) % 12
                    ]


@pytest.mark.parametrize("spec", VARGA_REGISTRY, ids=lambda spec: spec.code)
def test_every_chart_normalizes_longitudes(spec) -> None:
    assert spec.sign_fn is not None
    for longitude in (0.0, 1.234, 30.0, 179.123, 359.9999999):
        assert spec.sign_fn(longitude) == spec.sign_fn(longitude + 720)
        assert spec.sign_fn(longitude) == spec.sign_fn(longitude - 360)
