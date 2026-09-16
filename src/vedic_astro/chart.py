"""Composition root: wires ephemeris + astrology-logic modules into one KundaliChart."""

from __future__ import annotations

from vedic_astro.aspects import compute_aspects
from vedic_astro.dasha import compute_vimshottari_dasha
from vedic_astro.ephemeris import ascendant_longitude, house_cusps, planet_positions
from vedic_astro.jaimini import compute_chara_dasha, compute_chara_karakas
from vedic_astro.models import BirthData, HouseSystem, KundaliChart, Planet, PlanetPosition
from vedic_astro.nakshatra import nakshatra_for_longitude
from vedic_astro.panchanga import compute_panchanga
from vedic_astro.rashi_bhava import (
    build_ascendant,
    degree_in_sign,
    house_from_cusps,
    sign_for_longitude,
    whole_sign_house,
)
from vedic_astro.varga import hora_lord, hora_sign, navamsa_sign


def build_kundali_chart(birth_data: BirthData) -> KundaliChart:
    utc_dt = birth_data.utc_datetime
    raw_positions = planet_positions(utc_dt, birth_data.ayanamsha, birth_data.node_type)
    asc_longitude = ascendant_longitude(
        utc_dt, birth_data.latitude, birth_data.longitude, birth_data.ayanamsha
    )
    ascendant = build_ascendant(asc_longitude)

    cusps: list[float] | None = None
    if birth_data.house_system != HouseSystem.WHOLE_SIGN:
        cusps = house_cusps(
            utc_dt, birth_data.latitude, birth_data.longitude, birth_data.ayanamsha,
            birth_data.house_system,
        )

    planets: list[PlanetPosition] = []
    # raw_positions preserves the conventional Navagraha order (Sun..Saturn, Rahu, Ketu).
    for planet, raw in raw_positions.items():
        sign = sign_for_longitude(raw.longitude)
        house = (
            house_from_cusps(raw.longitude, cusps)
            if cusps is not None
            else whole_sign_house(sign, ascendant.sign)
        )
        planets.append(
            PlanetPosition(
                planet=planet,
                longitude=raw.longitude,
                sign=sign,
                degree_in_sign=degree_in_sign(raw.longitude),
                house=house,
                nakshatra=nakshatra_for_longitude(raw.longitude),
                retrograde=raw.retrograde,
                navamsa_sign=navamsa_sign(raw.longitude),
                hora_sign=hora_sign(raw.longitude),
                hora_lord=hora_lord(raw.longitude),
            )
        )

    moon_longitude = raw_positions[Planet.MOON].longitude
    panchanga = compute_panchanga(
        sun_longitude=raw_positions[Planet.SUN].longitude,
        moon_longitude=moon_longitude,
        local_date=birth_data.birth_date,
    )
    dasha = compute_vimshottari_dasha(
        moon_longitude=moon_longitude, birth_datetime=birth_data.local_datetime
    )

    return KundaliChart(
        birth_data=birth_data,
        ascendant=ascendant,
        planets=planets,
        panchanga=panchanga,
        dasha=dasha,
        aspects=compute_aspects(planets),
        chara_karakas=compute_chara_karakas(planets),
        chara_dasha=compute_chara_dasha(ascendant.sign, planets, birth_data.local_datetime),
    )
