"""Typed data shapes shared across the engine: birth input, computed chart output."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from enum import Enum

from pydantic import BaseModel, Field


class Sign(str, Enum):
    ARIES = "Aries"
    TAURUS = "Taurus"
    GEMINI = "Gemini"
    CANCER = "Cancer"
    LEO = "Leo"
    VIRGO = "Virgo"
    LIBRA = "Libra"
    SCORPIO = "Scorpio"
    SAGITTARIUS = "Sagittarius"
    CAPRICORN = "Capricorn"
    AQUARIUS = "Aquarius"
    PISCES = "Pisces"


SIGNS_IN_ORDER: list[Sign] = list(Sign)


class Planet(str, Enum):
    SUN = "Sun"
    MOON = "Moon"
    MARS = "Mars"
    MERCURY = "Mercury"
    JUPITER = "Jupiter"
    VENUS = "Venus"
    SATURN = "Saturn"
    RAHU = "Rahu"
    KETU = "Ketu"


class ChartStyle(str, Enum):
    SOUTH_INDIAN = "south_indian"
    NORTH_INDIAN = "north_indian"
    EAST_INDIAN = "east_indian"


class NodeType(str, Enum):
    MEAN = "mean"
    TRUE = "true"


class HouseSystem(str, Enum):
    WHOLE_SIGN = "whole_sign"
    EQUAL = "equal"
    PLACIDUS = "placidus"
    PORPHYRY = "porphyry"


class PlanetDignity(str, Enum):
    """Sign-level dignity only - see dignity.py. Rahu/Ketu are always
    NEUTRAL (their exaltation/debilitation is genuinely disputed across
    classical sources, not guessed here)."""

    EXALTED = "Exalted"
    DEBILITATED = "Debilitated"
    OWN_SIGN = "Own Sign"
    NEUTRAL = "Neutral"


class BirthData(BaseModel):
    name: str = ""  # display-only label, not used in any calculation
    birth_date: date
    birth_time: time
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    utc_offset_hours: float = Field(ge=-12, le=14)
    ayanamsha: str = "lahiri"
    node_type: NodeType = NodeType.MEAN
    chart_style: ChartStyle = ChartStyle.SOUTH_INDIAN
    house_system: HouseSystem = HouseSystem.WHOLE_SIGN

    @property
    def local_datetime(self) -> datetime:
        return datetime.combine(self.birth_date, self.birth_time)

    @property
    def utc_datetime(self) -> datetime:
        return self.local_datetime - timedelta(hours=self.utc_offset_hours)


class NakshatraPlacement(BaseModel):
    name: str
    index: int = Field(ge=1, le=27)
    pada: int = Field(ge=1, le=4)
    lord: Planet


class Ascendant(BaseModel):
    longitude: float = Field(ge=0, lt=360)
    sign: Sign
    degree_in_sign: float = Field(ge=0, lt=30)
    # Keyed by varga code ("D3", "D10", ...) - see divisional_charts.VARGA_REGISTRY.
    # Only codes with a built sign_fn are present.
    varga_signs: dict[str, Sign] = {}


class PlanetPosition(BaseModel):
    planet: Planet
    longitude: float = Field(ge=0, lt=360)
    sign: Sign
    degree_in_sign: float = Field(ge=0, lt=30)
    house: int = Field(ge=1, le=12)
    nakshatra: NakshatraPlacement
    retrograde: bool
    # Ecliptic latitude (degrees) and daily motion (degrees/day, negative =
    # retrograde) - raw ephemeris facts needed by shadbala.py (Ayana Bala's
    # declination, Chesta Bala's speed classification). 0.0 for Rahu/Ketu
    # (always treated as exactly on the ecliptic).
    ecliptic_latitude: float = 0.0
    speed_longitude: float = 0.0
    navamsa_sign: Sign | None = None
    hora_sign: Sign | None = None
    hora_lord: Planet | None = None
    # Keyed by varga code ("D3", "D10", ...) - see divisional_charts.VARGA_REGISTRY.
    # Only codes with a built sign_fn are present.
    varga_signs: dict[str, Sign] = {}
    # House under the Bhava Chalit (cusp-based, always Placidus) chart -
    # distinct from `house`, which follows the birth data's own house_system.
    bhava_chalit_house: int = Field(ge=1, le=12, default=1)
    dignity: PlanetDignity = PlanetDignity.NEUTRAL


class PanchangaElement(BaseModel):
    name: str
    index: int = Field(ge=1)


class PanchangaResult(BaseModel):
    tithi: PanchangaElement
    paksha: str
    vara: str
    nakshatra: PanchangaElement
    yoga: PanchangaElement
    karana: PanchangaElement


class DashaSubPeriod(BaseModel):
    """One sub-period of a dasha. Self-referential: Antardasha's sub_periods
    holds Pratyantardasha, whose sub_periods holds Sookshma, whose
    sub_periods holds Prana - the same proportional-subdivision rule at
    every level (see dasha.py). Empty by default; deeper levels are only
    computed on demand, not eagerly for the whole chart.
    """

    planet: Planet
    start: datetime
    end: datetime
    sub_periods: list["DashaSubPeriod"] = []


class DashaPeriod(BaseModel):
    planet: Planet
    start: datetime
    end: datetime
    sub_periods: list[DashaSubPeriod]


class VimshottariDasha(BaseModel):
    periods: list[DashaPeriod]

    def current_mahadasha(self, at: datetime) -> DashaPeriod | None:
        for period in self.periods:
            if period.start <= at < period.end:
                return period
        return None

    def current_antardasha(self, at: datetime) -> DashaSubPeriod | None:
        maha = self.current_mahadasha(at)
        if maha is None:
            return None
        for sub in maha.sub_periods:
            if sub.start <= at < sub.end:
                return sub
        return None


class PlanetAspect(BaseModel):
    source_planet: Planet
    source_house: int = Field(ge=1, le=12)
    target_planet: Planet
    target_house: int = Field(ge=1, le=12)
    is_special: bool


class CharaKaraka(BaseModel):
    planet: Planet
    karaka: str
    degree_in_sign: float = Field(ge=0, lt=30)


class NavataraEntry(BaseModel):
    nakshatra: str
    nakshatra_index: int = Field(ge=1, le=27)
    tara_category: str
    is_favorable: bool


class CharaDashaPeriod(BaseModel):
    sign: Sign
    lord: Planet
    years: float = Field(gt=0)
    start: datetime
    end: datetime


class ShaniDoshaResult(BaseModel):
    """Standalone Saturn-affliction check - see doshas.py. Always populated
    (has_house_dosha/has_neech_dosha drive UI styling only), same pattern
    as MangalDoshaResult in matching.py."""

    has_house_dosha: bool
    house_reason: str
    has_neech_dosha: bool
    neech_reason: str


class AshtakavargaSet(BaseModel):
    """Parasara Ashtakavarga only - see ashtakavarga.py. The Ascendant/
    Lagna's own individual BAV chart is intentionally not included here (no
    verified contribution table for it yet)."""

    bav_by_planet: dict[Planet, dict[Sign, int]]
    sav: dict[Sign, int]
    bhava_ashtakavarga: dict[int, int]


class SaturnPairDosha(BaseModel):
    """One Saturn-conjunction dosha (Vish/Shani Mangal/Shani Rahu) or the
    Jupiter-Rahu Guru Chandala dosha - always populated, see doshas.py /
    general_doshas.py."""

    name: str
    has_dosha: bool
    is_conjunction: bool  # False when triggered by aspect instead of same-house
    reason: str


class SaturnAfflictionDoshas(BaseModel):
    vish_dosha: SaturnPairDosha
    shani_mangal_dosha: SaturnPairDosha
    shani_rahu_dosha: SaturnPairDosha


class TransitSegment(BaseModel):
    """One maximal same-sign span of a transiting planet - see
    saturn_transit.py. Consecutive segments in a timeline always have
    different signs."""

    start: datetime
    end: datetime
    sign: Sign


class SadeSatiSegment(BaseModel):
    phase: int = Field(ge=1, le=3)
    segment: TransitSegment


class SadeSatiCycle(BaseModel):
    """One ~29.5-year-apart occurrence of the full Sade Sati trio. segments
    is chronological and may repeat/jump phase numbers if a retrograde dip
    revisited an earlier phase's sign - reported as it happened."""

    segments: list[SadeSatiSegment]
    start: datetime
    end: datetime
    truncated_at_start: bool
    truncated_at_end: bool


class TransitOccurrence(BaseModel):
    """One clustered episode of Saturn occupying a single target sign
    (Kantaka Shani or transit Ashtama Shani) - segments captures every
    retrograde-driven revisit, not just first-entry/final-exit."""

    segments: list[TransitSegment]
    start: datetime
    end: datetime
    truncated_at_start: bool
    truncated_at_end: bool


class KantakaShaniHouse(BaseModel):
    house: int = Field(ge=1, le=12)  # 4, 7, or 10
    occurrences: list[TransitOccurrence]


class SaturnTransitTimeline(BaseModel):
    """See saturn_transit.py. Computed once per chart (birth -> birth+100
    years); Sade Sati / Kantaka Shani / transit Ashtama Shani are all
    derived from the same underlying scan."""

    sade_sati_cycles: list[SadeSatiCycle]
    kantaka_shani_from_moon: list[KantakaShaniHouse]
    kantaka_shani_from_lagna: list[KantakaShaniHouse]
    ashtama_shani_transit: list[TransitOccurrence]
    scan_start: datetime
    scan_end: datetime


class KalasarpaDoshaResult(BaseModel):
    """See general_doshas.py. dosha_type is one of the 12 classically-named
    types (by Rahu's house from Lagna), only set when has_dosha is True."""

    has_dosha: bool
    dosha_type: str | None
    rahu_house: int = Field(ge=1, le=12)
    reason: str


class KujaDoshaReferencePoint(BaseModel):
    reference: str  # "Lagna", "Moon", or "Venus"
    has_dosha: bool
    mars_house: int = Field(ge=1, le=12)
    reason: str


class KujaDoshaResult(BaseModel):
    """See general_doshas.py. The classical 3-reference-point ('all types')
    Kuja/Mangal/Angaraka Dosha check - distinct from and additive to
    matching.py's Lagna-only mangal_dosha() used in two-person matching."""

    reference_points: list[KujaDoshaReferencePoint]
    overall_classification: str  # "High/Full Manglik", "Low/Partial Manglik", "Not Manglik"


class PunarphooDoshaResult(BaseModel):
    """See doshas.py. Forms via conjunction/aspect OR a mutual Nakshatra
    link between Saturn and the Moon; can be cancelled (Punarphoo Bhanga)
    by the Sun - see the two cancelled_by_* fields."""

    has_dosha: bool
    is_cancelled: bool
    conjunction_or_aspect: bool
    is_conjunction: bool
    moon_in_saturn_nakshatra: bool
    saturn_in_moon_nakshatra: bool
    cancelled_by_conjunction: bool
    cancelled_by_nakshatra: bool
    reason: str


class SthanaBalaBreakdown(BaseModel):
    """See shadbala.py. All values in virupas (60 virupas = 1 rupa)."""

    uchcha_bala: float
    saptavargaja_bala: float
    ojayugmarasyamsa_bala: float
    kendradi_bala: float
    drekkana_bala: float
    total: float


class KalaBalaBreakdown(BaseModel):
    """See shadbala.py. Masa Bala and Varsha Bala are deliberately not
    included - held pending a confirmed classical source for the month/
    year-lord determination algorithm (see the plan's scope decisions)."""

    nathonnata_bala: float
    paksha_bala: float
    tribhaga_bala: float
    dina_bala: float
    hora_bala: float
    ayana_bala: float
    total: float


class ShadbalaResult(BaseModel):
    """See shadbala.py. Computed only for the 7 classical planets (Sun
    through Saturn) - Rahu/Ketu are excluded, matching dignity.py's own
    exclusion of the lunar nodes from dignity scoring."""

    planet: Planet
    sthana_bala: SthanaBalaBreakdown
    dig_bala: float
    kala_bala: KalaBalaBreakdown
    chesta_bala: float
    naisargika_bala: float
    drik_bala: float
    total_virupas: float
    total_rupas: float
    required_rupas: float
    meets_required_strength: bool
    ishta_phala: float
    kashta_phala: float


class VimshopakaBalaResult(BaseModel):
    """See vimshopaka_bala.py. Shadvarga (6 charts) and Saptavarga (7
    charts) only - Dashavarga/Shodashavarga need divisional charts this
    app doesn't have built (D16, D60, and more - see the plan)."""

    planet: Planet
    shadvarga_score: float = Field(ge=0, le=20)
    saptavarga_score: float = Field(ge=0, le=20)
    shadvarga_band: str
    saptavarga_band: str


class BhavaBalaResult(BaseModel):
    """See bhava_bala.py. bhavadhipati_bala is the house lord's own total
    Shadbala (rupas) - a hard BPHS dependency, not computed independently."""

    house: int = Field(ge=1, le=12)
    bhavadhipati_bala: float
    bhava_dig_bala: float
    bhava_drishti_bala: float
    occupancy_adjustment: float
    diurnal_bonus: float
    total_rupas: float


class KundaliChart(BaseModel):
    birth_data: BirthData
    ascendant: Ascendant
    planets: list[PlanetPosition]
    panchanga: PanchangaResult
    dasha: VimshottariDasha
    aspects: list[PlanetAspect] = []
    chara_karakas: list[CharaKaraka] = []
    chara_dasha: list[CharaDashaPeriod] = []
    # Always computed with Placidus, independent of birth_data.house_system -
    # see divisional_charts.py / chart_render.bhava_chalit_layout.
    bhava_chalit_cusps: list[float] = []
    ashtakavarga: AshtakavargaSet | None = None
    shani_dosha: ShaniDoshaResult | None = None
    saturn_afflictions: SaturnAfflictionDoshas | None = None
    saturn_transit: SaturnTransitTimeline | None = None
    kalasarpa_dosha: KalasarpaDoshaResult | None = None
    kuja_dosha: KujaDoshaResult | None = None
    guru_chandala_dosha: SaturnPairDosha | None = None
    punarphoo_dosha: PunarphooDoshaResult | None = None
    shadbala: dict[Planet, ShadbalaResult] | None = None
    vimshopaka_bala: dict[Planet, VimshopakaBalaResult] | None = None
    bhava_bala: dict[int, BhavaBalaResult] | None = None


class KootaResult(BaseModel):
    name: str
    points_earned: float = Field(ge=0)
    max_points: float = Field(gt=0)
    reason: str


class MangalDoshaResult(BaseModel):
    has_dosha: bool
    mars_house: int = Field(ge=1, le=12)
    reason: str


class MatchReport(BaseModel):
    bride_moon_sign: Sign
    groom_moon_sign: Sign
    bride_nakshatra: str
    groom_nakshatra: str
    kootas: list[KootaResult]
    total_points: float
    max_points: float = 36
    verdict: str
    bride_mangal_dosha: MangalDoshaResult
    groom_mangal_dosha: MangalDoshaResult
    mangal_dosha_compatible: bool
