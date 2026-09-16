import pytest

from vedic_astro.matching import (
    bhakoot_koota,
    gana_koota,
    graha_maitri_koota,
    mangal_dosha,
    nadi_koota,
    tara_koota,
    varna_koota,
    vashya_koota,
    yoni_koota,
)
from vedic_astro.models import Sign


def test_varna_same_sign_is_compatible() -> None:
    result = varna_koota(Sign.CANCER, Sign.CANCER)
    assert result.points_earned == 1


def test_varna_groom_lower_than_bride_scores_zero() -> None:
    # Bride Cancer = Brahmin (rank 4), groom Gemini = Shudra (rank 1).
    result = varna_koota(Sign.CANCER, Sign.GEMINI)
    assert result.points_earned == 0


def test_varna_groom_higher_than_bride_scores_full() -> None:
    result = varna_koota(Sign.GEMINI, Sign.CANCER)
    assert result.points_earned == 1


def test_vashya_same_group_scores_full() -> None:
    result = vashya_koota(Sign.ARIES, Sign.TAURUS)  # both Chatushpada
    assert result.points_earned == 2


def test_vashya_different_group_scores_zero() -> None:
    result = vashya_koota(Sign.ARIES, Sign.SCORPIO)  # Chatushpada vs Keeta
    assert result.points_earned == 0


def test_tara_same_nakshatra_scores_zero() -> None:
    # Same nakshatra both ways -> classical inclusive counting: your own
    # nakshatra counted from itself is position 1 ("Janma"), an inauspicious
    # category - both directions agree, 0 points.
    result = tara_koota(1, 1)
    assert result.points_earned == 0.0


def test_tara_distinct_nakshatras_score_partial() -> None:
    # Ashwini(1) -> Rohini(4): one direction favorable, one not -> 1.5.
    result = tara_koota(1, 4)
    assert result.points_earned == 1.5


def test_tara_can_score_zero_for_a_genuinely_bad_pair() -> None:
    # Ashwini(1) and Magha(10) are both "Janma" from each other (9 apart,
    # same tara category) - both directions unfavorable, 0 points. This was
    # mathematically unreachable for any distinct pair before the off-by-one
    # fix to tara_category (see nakshatra.py) - now correctly reachable.
    result = tara_koota(1, 10)
    assert result.points_earned == 0.0


def test_tara_can_score_full_for_a_genuinely_good_pair() -> None:
    # Ashwini(1) and Bharani(2): both directions land on favorable
    # categories (Sampat/Parama Mitra) - full 3 points, without the
    # nakshatras being identical.
    result = tara_koota(1, 2)
    assert result.points_earned == 3.0


def test_yoni_same_animal_scores_full() -> None:
    # Ashwini(1) and Shatabhisha(24) are both Horse.
    result = yoni_koota(1, 24)
    assert result.points_earned == 4


def test_yoni_enemy_animals_score_zero() -> None:
    # Ashwini(1)=Horse, Hasta(13)=Buffalo -> natural enemies.
    result = yoni_koota(1, 13)
    assert result.points_earned == 0


def test_graha_maitri_same_lord_scores_full() -> None:
    result = graha_maitri_koota(Sign.CANCER, Sign.CANCER)
    assert result.points_earned == 5


def test_graha_maitri_mutual_friends_scores_full() -> None:
    # Leo (Sun) and Cancer (Moon): Sun and Moon are mutual friends.
    result = graha_maitri_koota(Sign.LEO, Sign.CANCER)
    assert result.points_earned == 5


def test_graha_maitri_mutual_enemies_scores_zero() -> None:
    # Leo (Sun) and Capricorn (Saturn): Sun and Saturn are mutual enemies.
    result = graha_maitri_koota(Sign.LEO, Sign.CAPRICORN)
    assert result.points_earned == 0


def test_gana_same_gana_scores_full() -> None:
    result = gana_koota(1, 5)  # Ashwini + Mrigashira, both Deva
    assert result.points_earned == 6


def test_gana_deva_rakshasa_scores_zero() -> None:
    result = gana_koota(1, 3)  # Ashwini (Deva) + Krittika (Rakshasa)
    assert result.points_earned == 0


def test_bhakoot_dosha_distance_scores_zero() -> None:
    # Aries to Taurus is a 2-count -> Bhakoot Dosha.
    result = bhakoot_koota(Sign.ARIES, Sign.TAURUS)
    assert result.points_earned == 0


def test_bhakoot_safe_distance_scores_full() -> None:
    # Aries to Leo is a 5-count from Aries... wait use a genuinely safe distance.
    result = bhakoot_koota(Sign.ARIES, Sign.CANCER)  # count = 4, not a dosha distance
    assert result.points_earned == 7


def test_nadi_same_nadi_scores_zero() -> None:
    # Ashwini and Ardra are both Aadi Nadi.
    result = nadi_koota(1, 6)
    assert result.points_earned == 0


def test_nadi_different_nadi_scores_full() -> None:
    # Ashwini (Aadi) and Bharani (Madhya).
    result = nadi_koota(1, 2)
    assert result.points_earned == 8


@pytest.mark.parametrize(
    ("mars_house", "expected_dosha"),
    [(1, True), (2, True), (4, True), (7, True), (8, True), (12, True), (3, False), (5, False), (10, False)],
)
def test_mangal_dosha_houses(mars_house: int, expected_dosha: bool) -> None:
    result = mangal_dosha(mars_house)
    assert result.has_dosha is expected_dosha
