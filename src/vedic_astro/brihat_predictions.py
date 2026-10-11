"""Selected, source-linked readings from Aiyar's 1905 Brihat Jataka.

These are paraphrases of identified stanzas, not a statistical forecast. Sign
readings select some of a stanza's themes; they do not reproduce every claim.
Keep configuration detection in brihat_jataka and interpretation here so that
absent, superseded and cancelled yogas cannot acquire predictions by accident.
"""
from __future__ import annotations

from typing import Any, TypedDict
import re

from vedic_astro.models import KundaliChart, Planet, SIGNS_IN_ORDER
from vedic_astro.rashi_bhava import RASHI_LORD


class Reading(TypedDict):
    id: str
    category: str
    title: str
    summary: str
    evidence: list[str]
    chapter: int
    reference: str
    note: str
    plain_summary: str
    rule: str


class PeriodTheme(TypedDict):
    lord: str
    supportive: str
    challenging: str
    reference: str


# Aries through Pisces. The Moon chapter is an addition identified by this
# edition; all other planetary sign readings are in XVIII.1–19.
SIGN_READINGS: dict[str, list[tuple[int, str]]] = {
    "Sun": [
        (1, "Ability, recognition, travel and work involving arms are selected themes of this placement."),
        (1, "Trade in clothing and perfumes, alongside an interest in music, are the selected themes."),
        (2, "Grammar, astrology and the acquisition of wealth are emphasized."),
        (2, "Independent effort, service to others and tiring journeys are emphasized, with pressure on resources."),
        (2, "Power and activity connected with forests, mountains or cattle are emphasized."),
        (2, "Writing, painting, literature, mathematics and practical knowledge are emphasized."),
        (3, "Travel, alchemy and work connected with liquor production are selected themes."),
        (3, "Forceful action, knowledge of arms and work with poisons are selected themes; thoughtless effort is a challenge."),
        (3, "Recognition among learned people, independence, medicine, sculpture and wealth are emphasized."),
        (3, "Trading activity is emphasized, alongside limited resources and an excessive attachment to wealth."),
        (4, "The stanza emphasizes difficulty accumulating wealth and property."),
        (4, "Wealth through water-related products and recognition through relationships are emphasized."),
    ],
    "Moon": [
        (1, "Changeable plans, travel, quickly relenting after anger and fluctuating wealth are selected themes."),
        (2, "Patience, generosity, friendship and influence are emphasized, with comfort in the middle and later parts of life."),
        (3, "Quick understanding, wit, agreeable speech, learning, music, dance and communication are emphasized."),
        (4, "Friendships, property and an interest in astrology are emphasized; wealth is described as waxing and waning."),
        (5, "Firm principles, boldness, generosity and attachment to the mother are emphasized, alongside a strong temper."),
        (6, "Modesty, truthful speech, learning, music, painting, books and connections with foreign places are emphasized."),
        (7, "Learning, trade, generosity, family support and travel are emphasized, alongside friction with relatives."),
        (8, "Reserve, resourcefulness and connections with influential families are selected themes, alongside separation from parents."),
        (9, "Writing, eloquence, learning, fine arts, inventiveness and multiple undertakings are emphasized."),
        (10, "Family attachment, ready understanding, writing and travel are emphasized; work may proceed slowly."),
        (11, "Alternating rises and setbacks, friendship, perfumes and flowers, and endurance during travel are selected themes."),
        (12, "Learning, wealth from sea-related products, family affection and an interest in clothing are emphasized."),
    ],
    "Mars": [
        (5, "Command, commerce, travel, bold action and enjoyment of pleasures are emphasized."),
        (5, "Adornment, games and magical arts are selected themes; timidity and disregarding friends' advice are challenges."),
        (6, "Helping others, music, courage, fighting ability and frugality are emphasized."),
        (6, "Intelligence and earning through journeys by sea or work abroad are emphasized."),
        (7, "Endurance, journeys through forests and fearlessness are emphasized, alongside material hardship."),
        (6, "Helping others, music, courage, fighting ability and frugality are emphasized."),
        (5, "Adornment, games and magical arts are selected themes; timidity and disregarding friends' advice are challenges."),
        (5, "Command, commerce, travel, bold action and enjoyment of pleasures are emphasized."),
        (7, "Ministerial work, recognition and bravery are emphasized, alongside opposition from enemies."),
        (7, "Wealth, authority and command are emphasized."),
        (7, "Independence and wandering are selected themes, alongside material hardship."),
        (7, "Ministerial work, recognition and bravery are emphasized, alongside opposition from enemies."),
    ],
    "Mercury": [
        (8, "Risk-taking, gambling, argument and debt are selected themes of this placement."),
        (8, "Teaching, preaching, earning, generosity and respect for mentors are emphasized."),
        (9, "Sciences, music, dance, painting, articulate speech and comfort are emphasized."),
        (9, "Earning through water-related work is emphasized, alongside friction with relatives."),
        (10, "Travel is emphasized, alongside limited means and difficulty securing comfort or recognition."),
        (10, "Learning, generosity, patience, ingenuity, courage and comfort are emphasized."),
        (8, "Teaching, preaching, earning, generosity and respect for mentors are emphasized."),
        (8, "Risk-taking, gambling, argument and debt are selected themes of this placement."),
        (11, "Sciences, law and recognition from rulers are emphasized."),
        (11, "Service to others and sculpture are selected themes, alongside debt or work without adequate reward."),
        (11, "Service to others and sculpture are selected themes, alongside debt or work without adequate reward."),
        (11, "Friendliness, ready understanding and skill in crafts are emphasized."),
    ],
    "Jupiter": [
        (12, "Command, wealth, generosity, patience, recognition and family comfort are emphasized."),
        (12, "Comfort, wealth, friends, generosity and acceptance by others are emphasized."),
        (12, "Property, friendships, comfort and ministerial work are emphasized."),
        (13, "Resources, influence, intelligence and comfort are emphasized."),
        (13, "Resources, intelligence, comfort and command are emphasized."),
        (12, "Property, friendships, comfort and ministerial work are emphasized."),
        (12, "Comfort, wealth, friends, generosity and acceptance by others are emphasized."),
        (12, "Command, wealth, generosity, patience, recognition and family comfort are emphasized."),
        (13, "Administration, ministerial work, command and wealth are emphasized."),
        (13, "Limited wealth and sorrow are the selected challenges in this stanza."),
        (13, "Friendships and property are selected themes, with fluctuating resources; the stanza refers to the Moon-in-Cancer reading."),
        (13, "Administration, ministerial work, command and wealth are emphasized."),
    ],
    "Venus": [
        (14, "Relationship difficulties and pressure on family property are the selected challenges."),
        (14, "Wealth through one's own intelligence, recognition, standing among relatives and courage are emphasized."),
        (15, "Service to rulers, wealth and an interest in music are emphasized."),
        (16, "Emotional distress, pride, timidity and pressure on resources are selected challenges."),
        (16, "Wealth connected with relationships and support from a partner are selected themes."),
        (15, "Hard work is the selected theme of this placement."),
        (14, "Wealth through one's own intelligence, recognition, standing among relatives and courage are emphasized."),
        (14, "Relationship difficulties and pressure on family property are the selected challenges."),
        (16, "Good qualities and wealth are emphasized."),
        (15, "Being liked by others is emphasized, alongside dependence through relationships."),
        (15, "Being liked by others is emphasized, alongside dependence through relationships."),
        (16, "Learning, wealth, respect and popularity are emphasized."),
    ],
    "Saturn": [
        (17, "Wandering, attention to appearance and difficulty with friendship or intellectual recognition are selected themes."),
        (18, "Limited wealth and difficulties in relationships are selected challenges."),
        (17, "Writing, painting and official work are selected themes, alongside grief or material hardship."),
        (18, "Material hardship and separation from the mother are selected challenges."),
        (18, "Grief, burdens and limited recognition are selected challenges."),
        (17, "Writing, painting and official work are selected themes, alongside grief or material hardship."),
        (18, "Recognition, wealth and authority over a community, town or army are emphasized."),
        (17, "Constraint and difficulty sustaining work are selected challenges."),
        (19, "Loyal official service, leadership, wealth and good family connections are emphasized."),
        (19, "Property, community leadership and wealth acquired through one's own effort are emphasized."),
        (19, "Property, community leadership and wealth acquired through one's own effort are emphasized."),
        (19, "Loyal official service, leadership, wealth and good family connections are emphasized."),
    ],
}

# Prediction stanzas are distinct from the stanzas that define these shapes.
NABHASA_EFFECTS: dict[str, tuple[int, str]] = {
    "Rajju": (11, "Travel abroad is emphasized, alongside envy of others' resources."),
    "Musala": (11, "Respect, wealth and engagement in many undertakings are emphasized."),
    "Nala": (11, "Settled views, wealth and skill are emphasized."),
    "Srik / Mala": (11, "Comfort and luxury are emphasized."),
    "Sarpa": (11, "Difficulty and discomfort are emphasized."),
    "Gada": (13, "Ritual service, focused effort and wealth are emphasized."),
    "Sakata": (13, "Livelihood connected with carts or transport is emphasized."),
    "Vihaga": (13, "Messages and travel are emphasized, alongside quarrels."),
    "Sringataka": (13, "Happiness in the later part of life is emphasized."),
    "Hala": (13, "Agriculture is emphasized as a source of livelihood."),
    "Vajra": (14, "Comfort in the earlier and later parts of life, popularity and courage are emphasized."),
    "Yava": (14, "Power and comfort in the middle part of life are emphasized."),
    "Kamala": (14, "Recognition, happiness and varied accomplishments are emphasized."),
    "Vapi": (14, "Accumulating wealth and frugality are emphasized, alongside limited enjoyment of comfort."),
    "Yupa": (15, "Giving and ritual service are emphasized."),
    "Ishu / Bana": (15, "Work involving arrows or places of confinement is emphasized."),
    "Sakti": (15, "Material difficulty and limited reward from work are emphasized."),
    "Danda": (15, "Service to others and separation from affection are emphasized."),
    "Nau": (16, "Recognition, intermittent comfort and frugality are emphasized."),
    "Kuta": (16, "Work associated with guarding or places of confinement is a selected theme."),
    "Chhatra": (16, "Helping the community and comfort in later life are emphasized."),
    "Chapa": (16, "Conflict and comfort in the earlier and later parts of life are emphasized."),
    "Ardha Chandra": (17, "Popularity, an agreeable disposition and respect are emphasized."),
    "Samudra": (17, "Prosperity and comfort are emphasized."),
    "Chakra": (17, "Influence among rulers and deference from others are emphasized."),
    "Vallaki / Veena": (17, "Intelligence, music and dance are emphasized."),
    "Damini": (18, "Generosity, helping others and cattle-related resources are emphasized."),
    "Pasa": (18, "Wealth through proper means, family connections and helpers are emphasized."),
    "Kedara": (18, "Agriculture, helpfulness and good works are emphasized."),
    "Sula": (18, "Courage is emphasized, alongside financial pressure."),
    "Yuga": (19, "Material difficulty and departure from established customs are selected themes."),
    "Gola": (19, "Wandering and difficulty with resources or occupational skill are emphasized."),
}
LUNAR_EFFECTS: dict[str, tuple[int, str]] = {
    "Adhi": (2, "Influence, authority, comfort and wealth are described, subject to the planets' power and the stanza's qualifiers."),
    "Sunapha": (5, "Self-earned property, intelligence, wealth and recognition are emphasized."),
    "Anapha": (5, "Authority, self-restraint, reputation and comfort are emphasized."),
    "Durudhura": (6, "Wealth, comfort, generosity and support from helpers are emphasized."),
    "Kemadruma — primary condition": (6, "Hardship and dependence are described when the primary condition is present without the evaluated cancellations."),
}
PERIOD_THEMES: dict[str, tuple[int, str, str]] = {
    "Sun": (12, "Trade in perfumes or gold, state work, courage, perseverance, recognition and giving.", "Pressure involving authorities, relatives, resources or conflict."),
    "Moon": (13, "Food, milk, clothing, flowers, ritual service, learning, resources and reputation.", "Idle effort, loss of resources or judgment, and conflict with relatives or powerful people."),
    "Mars": (14, "Land, brothers, state work, wool and bold enterprise.", "Relationship conflict and harsh speech."),
    "Mercury": (15, "Messages, friends, mentors, learning, crafts, metals, property and recognition.", "Harsh speech, mental pressure and constraint."),
    "Jupiter": (16, "Worship, learning, ingenuity, generosity, diplomacy, authority, resources and friends.", "Strain from travel and quarrels."),
    "Venus": (17, "Art, music, comforts, clothing trade, agriculture, friendship and learning.", "Conflict with friends or authorities."),
    "Saturn": (18, "Service, local administration, grain, labour and authority.", "Delays, idle effort, resentment and pressure."),
}

EASY_READINGS = {
    ("Sun", "Leo"): "This placement points to taking charge and activity connected with nature, rural places or cattle.",
    ("Moon", "Capricorn"): "This placement connects with family attachment, quick understanding, writing and travel. Work may progress slowly.",
    ("Mars", "Cancer"): "This placement connects earning with sea journeys or working away from home.",
    ("Mercury", "Cancer"): "This placement connects earning with water-related work. Friction with relatives is a possible challenge.",
    ("Jupiter", "Pisces"): "This placement points to leadership, administration, advisory work and opportunities to earn wealth.",
    ("Venus", "Leo"): "This placement points to support through a partner or relationships, including financial support.",
    ("Saturn", "Aries"): "This placement points to restlessness and attention to appearance. Friendships and gaining recognition may take effort.",
}


def simple_wording(text: str) -> str:
    """Use everyday synonyms without adding new predictive rules."""
    replacements = {"ministerial work": "advisory or administrative work", "command": "leadership",
                    "avocation": "work", "frugality": "careful spending", "frugal": "careful with money",
                    "material hardship": "money difficulties", "material difficulty": "money difficulties",
                    "state work": "government-related work", "ritual service": "religious service",
                    "eloquence": "clear speaking", "ingenuity": "problem-solving skill",
                    "self-restraint": "self-control", "coercion": "force", "reputation": "reputation",
                    "the book's occupational themes": "these work areas", "are emphasized": "are highlighted",
                    "is emphasized": "is highlighted", "the stanza emphasizes": "this rule highlights",
                    "in this stanza": "in this rule", "the book's Ashtakavarga reading": "this calculation"}
    for old, new in replacements.items():
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    return text[:1].upper() + text[1:]


def build_predictions(chart: KundaliChart, report: dict[str, Any]) -> dict[str, Any]:
    readings: list[Reading] = []

    def add(key: str, category: str, title: str, summary: str, evidence: list[str],
            chapter: int, reference: str, note: str = "", rule: str = "", plain: str = "") -> None:
        readings.append(Reading(id=key, category=category, title=title, summary=summary,
                                evidence=evidence, chapter=chapter, reference=reference, note=note,
                                plain_summary=plain or simple_wording(summary), rule=rule))

    for row in report["strengths"]:
        planet = row["planet"]
        sign_index = next(i for i, sign in enumerate(SIGNS_IN_ORDER) if sign.value == row["sign"])
        verse, text = SIGN_READINGS[planet][sign_index]
        chapter = 17 if planet == "Moon" else 18
        note = ("Chapter XVII is a later addition identified by this edition. Its final stanza requires the Moon, sign and sign lord to have power."
                if planet == "Moon" else "Selected sign themes; the planet's power and the rest of the chart qualify their expression.")
        if planet == "Sun" and sign_index == 0:
            # XVIII.1 excludes the deep-exaltation point from its ordinary
            # Aries reading; the note supplies the separate 10-degree result.
            sun = next(p for p in chart.planets if p.planet == Planet.SUN)
            if abs(sun.degree_in_sign - 10) < 1e-8:
                text = "The deep-exaltation point emphasizes wealth, recognition, helpers and a settled life."
            else:
                note += " The 10° deep-exaltation point has a separate reading."
        if planet == "Mercury" and row["sign"] == "Cancer":
            note += " XVIII.9 records an alternative reading based on Mercury's strength."
        evidence = [f"D1 {planet} in {row['sign']}; Bhava {row['bhava']}; D9 {row['navamsa']}",
                    "Sthana: " + (", ".join(row["sthana"]) or "no evaluated support"),
                    f"Dig: {'supported' if row['dig'] else 'not supported'}; Chesta: {row['chesta']}",
                    f"Day/night: {'supported' if row['kala'] else 'not supported'}; Paksha: {'supported' if row['paksha'] else 'not supported'}"]
        add(f"sign-{planet.lower()}", "Planetary tendencies", f"{planet} in {row['sign']}", text,
            evidence, chapter, f"{'XVII' if chapter == 17 else 'XVIII'}.{verse}", note,
            "Use the planet's natal sign for its reading, then check placement, direction, motion and time support to qualify the result.",
            EASY_READINGS.get((planet, row["sign"]), ""))

    for row in report["career"]:
        add(f"career-{row['base'].lower()}", "Work & livelihood", f"Livelihood from {row['base']}",
            f"The {row['career_lord']} Navamsa-lord chain points to the book's occupational themes: {row['themes']}.",
            [f"10th from {row['base']}: {row['tenth']}",
             f"10th lord {row['lord']} → D9 {row['navamsa']} → lord {row['career_lord']}"],
            10, "X.1–3", "Compare all three reference points and their strength; this does not select a single profession.",
            f"Count 10 signs from {row['base']}. Find that sign's ruling planet, its D9 sign, then the D9 sign's ruling planet. Use the final planet for work themes.",
            f"This calculation ends with {row['career_lord']}. Its work areas are: {simple_wording(row['themes'])}. Compare the three calculations before choosing a work theme.")

    durudhura = any(row["name"] == "Durudhura" and row["matched"] for row in report["lunar"])
    for group, catalog, chapter, roman in [("lunar", LUNAR_EFFECTS, 13, "XIII"), ("nabhasa", NABHASA_EFFECTS, 12, "XII")]:
        for row in report[group]:
            if not row["matched"] or row.get("active") is False:
                continue
            if group == "lunar" and durudhura and row["name"] in ("Sunapha", "Anapha"):
                continue  # XIII.3 defines the both-sides form separately.
            verse, text = catalog[row["name"]]
            add(f"yoga-{group}-{row['name']}", "Matched yogas", row["name"], text,
                [row["condition"], f"Configuration rule: {row['reference']}"], chapter, f"{roman}.{verse}",
                "A traditional conditional reading, qualified by planetary power. Nabhasa themes describe the life broadly rather than a dated event."
                if group == "nabhasa" else "The configuration is present; its strength and other qualifiers still require judgment.", row["condition"])
    for row in report["raja"]:
        if row["matched"]:
            add(f"yoga-{row['name']}", "Matched yogas", row["name"],
                "This configuration is associated with authority and high standing in the classical text, subject to planetary power and context.",
                [row["condition"]], 11, row["reference"], rule=row["condition"])

    for row in report["ashtakavarga"]:
        count = row["bindus"]
        text = ("More than four bindus support favourable results." if count > 4 else
                "Fewer than four bindus indicate difficulty in the book's Ashtakavarga reading." if count < 4 else
                "Exactly four bindus give a mixed favourable and adverse reading.")
        add(f"bav-{row['planet'].lower()}", "Ashtakavarga", f"{row['planet']} · {row['reading'].lower()}", text,
            [f"{row['planet']} BAV in natal {row['sign']}: {count} of 8 bindus"], 9, "IX.8",
            "This reads the natal occupied sign; transit readings require the planet's sign on the chosen transit date.",
            "Count the planet's bindus in its natal sign: 0–3 means less support; 4 is mixed; 5–8 means more support.",
            f"Your {row['planet']} has {count} of 8 bindus in {row['sign']}. " +
            ("This gives more support in this calculation." if count > 4 else "This gives less support in this calculation." if count < 4 else "This gives a mixed result in this calculation."))

    themes: list[PeriodTheme] = [PeriodTheme(lord=planet, supportive=good, challenging=bad,
                                           reference=f"VIII.{verse}")
                               for planet, (verse, good, bad) in PERIOD_THEMES.items()]
    ascendant_lord = RASHI_LORD[chart.ascendant.sign].value
    verse, good, bad = PERIOD_THEMES[ascendant_lord]
    themes.append(PeriodTheme(lord="Lagna", supportive=good, challenging=bad,
                              reference=f"VIII.19; rising lord {ascendant_lord}: VIII.{verse}"))
    return {"readings": readings, "period_themes": themes, "lagna_lord": ascendant_lord,
            "source_edition": "N. Chidambaram Aiyar, 1905",
            "scope": "Selected traditional readings from the natal chart and your calculated Brihat Jataka dasha worksheet. These are conditional themes, not guaranteed events.",
            "timing_note": "The dates follow the selected Pinda/Amsa worksheet and Savana-year convention. VIII.10–11 also require a chart at dasha commencement; that chart is not calculated here. Supportive and challenging themes are shown together because their expression needs further judgment."}
