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


class PlanetPosition(BaseModel):
    planet: Planet
    longitude: float = Field(ge=0, lt=360)
    sign: Sign
    degree_in_sign: float = Field(ge=0, lt=30)
    house: int = Field(ge=1, le=12)
    nakshatra: NakshatraPlacement
    retrograde: bool
    navamsa_sign: Sign | None = None
    hora_sign: Sign | None = None
    hora_lord: Planet | None = None


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


class KundaliChart(BaseModel):
    birth_data: BirthData
    ascendant: Ascendant
    planets: list[PlanetPosition]
    panchanga: PanchangaResult
    dasha: VimshottariDasha
    aspects: list[PlanetAspect] = []
    chara_karakas: list[CharaKaraka] = []
    chara_dasha: list[CharaDashaPeriod] = []


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
