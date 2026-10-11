"""Composition root: wires ephemeris + astrology-logic modules into one KundaliChart."""

from __future__ import annotations

from vedic_astro.ashtakavarga import compute_ashtakavarga
from vedic_astro.aspects import compute_aspects
from vedic_astro.bcp import compute_bcp_longevity, compute_bhrigu_chakra
from vedic_astro.bhava_bala import compute_bhava_bala
from vedic_astro.bhrigu_nandi_nadi import compute_bhrigu_nandi_nadi
from vedic_astro.bsp import (
    compute_bsp_aries_spoilt, compute_bsp_house_notes, compute_bsp_rules, compute_bsp_venus_reveals,
)
from vedic_astro.dasha import compute_vimshottari_dasha
from vedic_astro.dignity import planet_dignity
from vedic_astro.divisional_charts import VARGA_REGISTRY, dwadasamsa_sign
from vedic_astro.doshas import compute_punarphoo_dosha, compute_saturn_afflictions, compute_shani_dosha
from vedic_astro.ephemeris import ascendant_longitude, house_cusps, planet_positions
from vedic_astro.general_doshas import (
    compute_guru_chandala_dosha,
    compute_kalasarpa_dosha,
    compute_kuja_dosha,
)
from vedic_astro.jaimini import compute_chara_dasha, compute_chara_karakas
from vedic_astro.models import BirthData, HouseSystem, KundaliChart, Planet, PlanetPosition, Sign
from vedic_astro.nakshatra import nakshatra_for_longitude
from vedic_astro.padma_chakra import compute_badhaka, compute_padma_chakra_years
from vedic_astro.panchanga import compute_panchanga
from vedic_astro.rashi_bhava import (
    build_ascendant,
    degree_in_sign,
    house_from_cusps,
    sign_for_longitude,
    whole_sign_house,
)
from vedic_astro.saturn_transit import compute_saturn_transit_timeline
from vedic_astro.shadbala import compute_shadbala
from vedic_astro.varga import hora_lord, hora_sign, navamsa_sign
from vedic_astro.vimshopaka_bala import compute_vimshopaka_bala


def _built_varga_signs(longitude: float) -> dict[str, Sign]:
    return {
        spec.code: spec.sign_fn(longitude)
        for spec in VARGA_REGISTRY
        if spec.sign_fn is not None
    }


def build_kundali_chart(birth_data: BirthData) -> KundaliChart:
    utc_dt = birth_data.utc_datetime
    raw_positions = planet_positions(utc_dt, birth_data.ayanamsha, birth_data.node_type)
    asc_longitude = ascendant_longitude(
        utc_dt, birth_data.latitude, birth_data.longitude, birth_data.ayanamsha
    )
    ascendant = build_ascendant(asc_longitude)
    ascendant = ascendant.model_copy(update={"varga_signs": _built_varga_signs(asc_longitude)})

    cusps: list[float] | None = None
    if birth_data.house_system != HouseSystem.WHOLE_SIGN:
        cusps = house_cusps(
            utc_dt, birth_data.latitude, birth_data.longitude, birth_data.ayanamsha,
            birth_data.house_system,
        )

    # Bhava Chalit is always computed on Placidus, independent of the birth
    # data's own house_system setting (which only ever affects the `house`
    # column above) - otherwise it would be visually identical to the D1
    # chart whenever the user has Whole Sign selected.
    bhava_chalit_cusps = house_cusps(
        utc_dt, birth_data.latitude, birth_data.longitude, birth_data.ayanamsha,
        HouseSystem.PLACIDUS,
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
                ecliptic_latitude=raw.latitude,
                speed_longitude=raw.speed_longitude,
                navamsa_sign=navamsa_sign(raw.longitude),
                hora_sign=hora_sign(raw.longitude),
                hora_lord=hora_lord(raw.longitude),
                varga_signs=_built_varga_signs(raw.longitude),
                bhava_chalit_house=house_from_cusps(raw.longitude, bhava_chalit_cusps),
                dignity=planet_dignity(planet, sign),
            )
        )

    moon_longitude = raw_positions[Planet.MOON].longitude
    panchanga = compute_panchanga(
        sun_longitude=raw_positions[Planet.SUN].longitude,
        moon_longitude=moon_longitude,
        local_date=birth_data.birth_date,
        birth_data=birth_data,
    )
    dasha = compute_vimshottari_dasha(
        moon_longitude=moon_longitude, birth_datetime=birth_data.local_datetime
    )

    aspects = compute_aspects(planets)
    moon_sign = next(p.sign for p in planets if p.planet == Planet.MOON)
    moon_is_waxing = panchanga.paksha == "Shukla"

    shadbala = compute_shadbala(planets, ascendant.sign, bhava_chalit_cusps, aspects, birth_data, moon_is_waxing)
    vimshopaka_bala = compute_vimshopaka_bala(planets)
    bhava_bala = compute_bhava_bala(planets, bhava_chalit_cusps, ascendant.sign, shadbala, moon_is_waxing)

    return KundaliChart(
        birth_data=birth_data,
        ascendant=ascendant,
        planets=planets,
        panchanga=panchanga,
        dasha=dasha,
        aspects=aspects,
        chara_karakas=compute_chara_karakas(planets),
        chara_dasha=compute_chara_dasha(ascendant.sign, planets, birth_data.local_datetime),
        bhava_chalit_cusps=bhava_chalit_cusps,
        ashtakavarga=compute_ashtakavarga(planets, ascendant.sign, bhava_chalit_cusps),
        shani_dosha=compute_shani_dosha(planets),
        saturn_afflictions=compute_saturn_afflictions(planets, aspects),
        saturn_transit=compute_saturn_transit_timeline(birth_data, moon_sign, ascendant.sign),
        kalasarpa_dosha=compute_kalasarpa_dosha(planets),
        kuja_dosha=compute_kuja_dosha(planets, ascendant.sign),
        guru_chandala_dosha=compute_guru_chandala_dosha(planets, aspects),
        punarphoo_dosha=compute_punarphoo_dosha(planets, aspects),
        shadbala=shadbala,
        vimshopaka_bala=vimshopaka_bala,
        bhava_bala=bhava_bala,
        bhrigu_chakra=compute_bhrigu_chakra(ascendant.sign, planets),
        bcp_longevity=compute_bcp_longevity(ascendant.sign, planets),
        bsp_rules=compute_bsp_rules(ascendant.sign, planets, aspects, require_special_status=False),
        bsp_house_notes=compute_bsp_house_notes(ascendant.sign, planets),
        bsp_aries_spoilt=compute_bsp_aries_spoilt(ascendant.sign, planets),
        bsp_venus_reveals=compute_bsp_venus_reveals(ascendant.sign, planets),
        badhaka_d1=compute_badhaka(ascendant.sign),
        badhaka_d12=compute_badhaka(dwadasamsa_sign(ascendant.longitude)),
        bnn=compute_bhrigu_nandi_nadi(planets),
        padma_chakra=compute_padma_chakra_years(
            ascendant.sign, ascendant.longitude, planets, birth_data.local_datetime
        ),
    )
