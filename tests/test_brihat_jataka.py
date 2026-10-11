"""Examples from the 1905 edition plus period/coverage invariants."""
from datetime import datetime
from fractions import Fraction
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from vedic_astro.brihat_jataka import (
    CLASSICAL, DashaOptions, NATURAL_ORDER, amsa_base, amsa_multiplier,
    antardasha_weights, aspect_fraction, ayurdaya_worksheet, book_source,
    dasha_timeline, lagna_quality, lunar_yogas, nabhasa_yogas, pinda_base,
)
from vedic_astro.models import Planet, PlanetPosition, Sign, SIGNS_IN_ORDER
from vedic_astro.nakshatra import nakshatra_for_longitude
from vedic_astro.rashi_bhava import sign_for_longitude
from vedic_astro.web.app import app


def position(planet: Planet, longitude: float, retrograde: bool = False) -> PlanetPosition:
    return PlanetPosition(planet=planet, longitude=longitude, sign=sign_for_longitude(longitude),
                          degree_in_sign=longitude % 30, house=1, nakshatra=nakshatra_for_longitude(longitude),
                          retrograde=retrograde)


def sample() -> list[PlanetPosition]:
    # VII.6 commentator's worked example: all exalted except Mercury.
    return [position(p, lon) for p, lon in zip(CLASSICAL, [10, 33, 298, 30+25/60, 95, 357, 200])]


@pytest.mark.parametrize("p,exalt,max_years", [
    (Planet.SUN,10,19), (Planet.MOON,33,25), (Planet.MARS,298,15),
    (Planet.MERCURY,165,12), (Planet.JUPITER,95,15), (Planet.VENUS,357,21), (Planet.SATURN,200,20),
])
def test_vii_1_2_years_and_angular_interpolation(p, exalt, max_years):
    assert pinda_base(p, exalt) == max_years
    assert pinda_base(p, (exalt+180)%360) == max_years/2
    assert pinda_base(p, (exalt+90)%360) == max_years*.75
    assert pinda_base(p, (exalt-90)%360) == max_years*.75


def test_vii_6_commentary_120_years_and_five_days():
    # The book uses the END of Pisces, a limit just before 360°, giving 9
    # Lagna years. Use that limit without violating longitude < 360.
    result = ayurdaya_worksheet(sample(), 360-1e-10, DashaOptions(model="pinda"))
    by = {r["lord"]: r for r in result["rows"]}
    assert by["Mars"]["final_years"] == 7.5  # 11th, half lost
    assert by["Saturn"]["final_years"] == 16  # 8th, one fifth lost
    assert by["Mercury"]["final_years"] == pytest.approx(7.5+5/360)
    assert result["total"] == pytest.approx(120+5/360)
    assert result["krurodaya_loss"] == 0


def test_vii_10_suns_worked_amsa_example():
    # 115°13′ -> 10y 6m 23d 24 ghatikas, 30d month and 60 gh/day.
    assert amsa_base(115+13/60) == pytest.approx(10+.5+23/360+24/(60*360))


def test_vii_13_multipliers_never_stack():
    assert amsa_multiplier(position(Planet.MERCURY,165,True)) == 3
    assert amsa_multiplier(position(Planet.MERCURY,60)) == 2
    assert amsa_multiplier(position(Planet.SUN,48)) == 1


def test_greater_enemy_or_combustion_loss_and_vakra_variant():
    planets = sample()
    planets[0] = position(Planet.SUN,105)
    planets[3] = position(Planet.MERCURY,106,True)  # Cancer: enemy Moon, also combust
    options = DashaOptions(model="pinda", vakra_exemption="mars")
    row = ayurdaya_worksheet(planets,340,options)["rows"][3]
    assert row["enemy_loss"] == "1/3" and row["combust_loss"] == "1/2"
    assert row["years"] == pytest.approx(row["base"] / 2)
    row = ayurdaya_worksheet(planets,340,DashaOptions(model="pinda"))["rows"][3]
    assert row["enemy_loss"] == "0"  # author's retrograde exemption


def test_chakrapata_reduces_only_strongest_in_same_sign():
    planets = [position(p,195+i) for i,p in enumerate(CLASSICAL)]
    result = ayurdaya_worksheet(planets,10,DashaOptions(model="pinda"))
    assert [r["lord"] for r in result["rows"] if r["chakra_loss"] != "0"] == ["Sun"]
    reversed_order = NATURAL_ORDER[::-1]
    result = ayurdaya_worksheet(planets,10,DashaOptions(model="pinda",priority=reversed_order))
    assert [r["lord"] for r in result["rows"] if r["chakra_loss"] != "0"] == ["Saturn"]


def test_viii_4_worked_antardasha_ratio():
    signs = {"Sun": Sign.ARIES, "Moon": Sign.ARIES, "Mars": Sign.LEO,
             "Mercury": Sign.CANCER, "Jupiter": Sign.TAURUS, "Venus": Sign.GEMINI,
             "Saturn": Sign.AQUARIUS, "Lagna": Sign.ARIES}
    weights = antardasha_weights("Sun", signs, NATURAL_ORDER)
    assert [name for name, _ in weights] == ["Sun", "Moon", "Mars", "Mercury"]
    denominator = sum((w for _,w in weights),Fraction(0))
    assert [w/denominator for _,w in weights] == [Fraction(12,25),Fraction(6,25),Fraction(4,25),Fraction(3,25)]


@pytest.mark.parametrize("model", ["pinda", "amsa"])
@pytest.mark.parametrize("seed", ["Sun", "Moon", "Lagna"])
def test_periods_have_all_eight_owners_and_close_exactly(model, seed):
    start = datetime(1990,6,15,8,30)
    result = dasha_timeline(sample(),350,start,DashaOptions(model=model,seed=seed))
    periods = result["periods"]
    assert periods[0]["lord"] == seed
    assert set(p["lord"] for p in periods) == set(NATURAL_ORDER)
    assert periods[0]["start"] == start.isoformat()
    for i,p in enumerate(periods):
        sub = p["sub_periods"]
        assert sub[0]["start"] == p["start"] and sub[-1]["end"] == p["end"]
        assert sum((Fraction(s["share"]) for s in sub), Fraction(0)) == 1
        assert all(s["end"] == sub[j+1]["start"] for j,s in enumerate(sub[:-1]))
        assert p["years"] >= 0
        if i: assert p["start"] == periods[i-1]["end"]


def test_ii_13_aspect_bands_are_directed_and_use_special_full_strength():
    assert aspect_fraction(position(Planet.SUN,350),50) == .25
    assert aspect_fraction(position(Planet.SATURN,350),50) == 1
    assert aspect_fraction(position(Planet.JUPITER,20),140) == 1
    assert aspect_fraction(position(Planet.MARS,20),110) == 1
    assert aspect_fraction(position(Planet.SUN,20),50) == 0
    assert aspect_fraction(position(Planet.SUN,20),200) == 1
    assert aspect_fraction(position(Planet.SUN,20),215) == 0  # boundary outside 30° span


def test_viii_8_all_lagna_quality_modes():
    assert [lagna_quality(x) for x in [5,15,25]] == ["Uttama","Madhyama","Adhama"]
    assert [lagna_quality(x) for x in [35,45,55]] == ["Adhama","Uttama","Madhyama"]
    assert [lagna_quality(x) for x in [65,75,85]] == ["Adhama","Madhyama","Uttama"]


def test_xii_all_32_forms_and_gola_precedence():
    planets = [position(p,65+i) for i,p in enumerate(CLASSICAL)]
    rows = nabhasa_yogas(planets,Sign.GEMINI,{p:1 for p in CLASSICAL})
    assert len(rows) == 32
    assert next(r for r in rows if r["name"] == "Gola")["active"]
    assert next(r for r in rows if r["name"] == "Nala")["matched"]
    assert not next(r for r in rows if r["name"] == "Nala")["active"]


def test_xii_gada_supersedes_sankhya_yuga():
    planets = [position(p,5 if i<4 else 95) for i,p in enumerate(CLASSICAL)]
    rows = nabhasa_yogas(planets,Sign.ARIES,{p:1 if i<4 else 4 for i,p in enumerate(CLASSICAL)})
    assert next(r for r in rows if r["name"] == "Gada")["active"]
    assert not next(r for r in rows if r["name"] == "Yuga")["active"]


def test_xiii_nodes_and_sun_do_not_form_sunapha():
    planets = [position(p,5) for p in CLASSICAL]
    planets += [position(Planet.RAHU,35),position(Planet.KETU,215)]
    planets[0] = position(Planet.SUN,35)
    rows = lunar_yogas(planets,Sign.CANCER)
    assert not next(r for r in rows if r["name"] == "Sunapha")["matched"]


def test_invalid_power_order_is_rejected():
    with pytest.raises(ValidationError): DashaOptions(priority=["Sun"]*8)


def test_book_packaging_preserves_every_byte_of_source():
    raw = (Path(__file__).parents[1]/"docs/sources/brihat-jataka-1905.txt").read_bytes()
    book = book_source()
    full = book["front_matter"] + "".join(c["text"] for c in book["chapters"]) + book["appendix"]
    assert full.encode("utf-8") == raw
    assert book["sha256"] == hashlib.sha256(raw).hexdigest()
    assert [c["number"] for c in book["chapters"]] == list(range(1,29))
    assert all(len(c["text"]) > 1000 for c in book["chapters"])
    assert [c["number"] for c in book["chapters"] if c["edition_addition"]] == [16,17]


def test_local_book_routes_and_dasha_input_validation():
    client = TestClient(app)
    assert len(client.get('/api/brihat-jataka/book').json()['chapters']) == 28
    assert 'Conclusion' in client.get('/brihat-jataka/book/28').text
    assert client.get('/brihat-jataka/book/29').status_code == 404
    assert client.post('/api/brihat-jataka/dasha',json={}).status_code == 422
    assert client.get('/brihat-jataka/source.txt').content == (Path(__file__).parents[1]/'docs/sources/brihat-jataka-1905.txt').read_bytes()


def test_dasha_endpoint_changes_method_and_seed_without_full_chart():
    response = TestClient(app).post('/api/brihat-jataka/dasha',json={
        'birth_data': {'birth_date':'1990-06-15','birth_time':'08:30:00','latitude':13.0827,'longitude':80.2707,'utc_offset_hours':5.5},
        'options': {'model':'pinda','seed':'Moon'},
    })
    assert response.status_code == 200
    result = response.json()
    assert result['periods'][0]['lord'] == 'Moon'
    assert result['worksheet']['options']['model'] == 'pinda'
    assert len(result['periods']) == 8
