"""Condition-based readings for Jaimini 2's declared book conventions."""
from __future__ import annotations

from typing import Any

from vedic_astro.aspects import sign_aspects
from vedic_astro.dignity import DEBILITATION_SIGN
from vedic_astro.jaimini2 import exalted, lord, passed, step
from vedic_astro.jaimini2_dasha import d9_positions
from vedic_astro.models import KundaliChart, Planet, PlanetPosition, Sign
from vedic_astro.varga import navamsa_sign

Row = dict[str, Any]
MALEFICS = {Planet.SUN, Planet.MARS, Planet.SATURN, Planet.RAHU, Planet.KETU}
OCCUPATIONS = {
    Planet.SUN: 'administration and public responsibilities', Planet.MOON: 'property and construction',
    Planet.MARS: 'technical, defence and legal work', Planet.MERCURY: 'commerce, distribution and mediation',
    Planet.JUPITER: 'teaching, law and academic study', Planet.VENUS: 'creative arts and media',
    Planet.SATURN: 'independent work and leadership', Planet.RAHU: 'industry and media',
    Planet.KETU: 'philosophy and commission-based trade',
}


def check(code: str, topic: str, present: bool, tone: str, summary: str, evidence: str, rule: str) -> Row:
    return dict(code=code, topic=topic, present=present, tone=tone, summary=summary, evidence=evidence, rule=rule)


def assess(conditions: list[Row]) -> Row:
    active = [c for c in conditions if c['present']]
    tones = {c['tone'] for c in active}
    tone = ('mixed' if 'mixed' in tones or {'supportive', 'challenging'} <= tones else
            'supportive' if 'supportive' in tones else 'challenging' if 'challenging' in tones else 'neutral')
    summaries = {
        'supportive': 'The checked rules show supportive indications for this reading.',
        'challenging': 'The checked rules show pressure or obstacles to work through.',
        'mixed': 'Support and pressure occur together; read the individual conditions below.',
        'neutral': 'The checked rules do not establish a clear good or difficult result.',
    }
    return {'tone': tone, 'summary': summaries[tone], 'supportive': sum(c['tone'] == 'supportive' for c in active),
            'challenging': sum(c['tone'] == 'challenging' for c in active), 'conditions': conditions}


def names(planets: list[PlanetPosition]) -> str:
    return ', '.join(p.planet.value for p in planets) or 'none'


def connected(sign: Sign, planets: list[PlanetPosition]) -> list[PlanetPosition]:
    return [p for p in planets if p.sign == sign or sign in sign_aspects(p.sign)]


def benefics(planets: list[PlanetPosition], natal: list[PlanetPosition]) -> set[Planet]:
    by = {p.planet: p for p in natal}
    result = {Planet.JUPITER, Planet.VENUS}
    if (by[Planet.MOON].longitude - by[Planet.SUN].longitude) % 360 < 180:
        result.add(Planet.MOON)
    if not any(p.planet in MALEFICS and p.sign == next(q.sign for q in planets if q.planet == Planet.MERCURY) for p in planets):
        result.add(Planet.MERCURY)
    return result


def module(code: str, title: str, basis: str, anchor: Sign, conditions: list[Row], facts: list[Row]) -> Row:
    return {'id': code, 'title': title, 'basis': basis, 'anchor': anchor.value, 'facts': facts, **assess(conditions)}


def fact(label: str, value: str) -> Row:
    return {'label': label, 'value': value}


def arudha_reading(chart: KundaliChart, padas: list[Row]) -> Row:
    ps = chart.planets
    al = Sign(padas[0]['sign'])
    gain, second = step(al, 10), step(al, 1)
    bs = benefics(ps, ps)
    gain_ps = [p for p in ps if p.sign == gain and (p.planet in bs or exalted(p))]
    a7 = Sign(padas[6]['sign'])
    distance = passed(al, a7, 1) + 1
    moon_venus = all(any(p.planet == name and p.sign == second for p in ps) for name in (Planet.MOON, Planet.VENUS))
    conditions = [
        check('al-eleventh', 'Income and gains', bool(gain_ps), 'supportive',
              'The eleventh from AL has a benefic or exalted occupant, a supportive wealth indication.',
              f'AL {al.value}; H11 {gain.value}; qualifying occupants: {names(gain_ps)}.',
              'A benefic or exalted planet occupying the eleventh from AL supports the wealth condition.'),
        check('al-a7-support', 'Partnership and public standing', distance in (1, 3, 4, 5, 7, 9, 10, 11), 'supportive',
              'A7 has a supportive house relationship with AL for gains and public dealings.',
              f'A7 {a7.value} is H{distance} from AL {al.value}.',
              'A7 in a kendra, trine, third or eleventh from AL meets the supportive arudha relationship.'),
        check('al-a7-pressure', 'Effort needed for gains', distance in (6, 8, 12), 'challenging',
              'A7 falls in a difficult relationship to AL, indicating extra effort in earning and partnerships.',
              f'A7 {a7.value} is H{distance} from AL {al.value}.', 'A7 in sixth, eighth or twelfth from AL is the challenging relationship.'),
        check('al-moon-venus', 'Resources and comforts', moon_venus, 'supportive',
              'Moon and Venus together in the second from AL meet a wealth-supporting combination.',
              f'H2 from AL is {second.value}; occupants: {names([p for p in ps if p.sign == second])}.',
              'Check joint occupation by Moon and Venus in the second from AL.'),
    ]
    result = module('arudha', 'Arudha Lagna & all padas', 'D1', al, conditions,
                    [fact('Arudha Lagna', al.value), fact('AL lord', lord(al, ps).value),
                     fact('Income sign · H11', gain.value), fact('Darapada · A7', a7.value)])
    result['padas'] = [{**p, 'occupants': names([q for q in ps if q.sign.value == p['sign']]),
                        'aspecting': names([q for q in ps if Sign(p['sign']) in sign_aspects(q.sign)])} for p in padas]
    return result


def upapada_reading(chart: KundaliChart, ks: list[Row], ul: Sign, name: str, calculation: str) -> Row:
    ps = chart.planets
    second, seventh = step(ul, 1), step(ul, 6)
    links = connected(second, ps)
    support = [p for p in links if p.planet in benefics(ps, ps)]
    pressure = [p for p in links if p.planet in (Planet.SATURN, Planet.RAHU)]
    dk9 = Sign(ks[-1]['navamsa_sign'])
    conditions = [
        check('ul-second-benefic', 'Relationship support', bool(support), 'supportive',
              'Benefic connections to the second from UL support the relationship reading.',
              f'UL {ul.value}; H2 {second.value}; benefic occupants/aspects: {names(support)}.',
              'Check benefic occupation or rashi aspect to the second from the selected Upapada.'),
        check('ul-second-saturn-rahu', 'Relationship pressure', bool(pressure), 'challenging',
              'Saturn or Rahu connects to the second from UL. Communication and external pressure need closer attention.',
              f'H2 {second.value}; Saturn/Rahu connections: {names(pressure)}.',
              'The second-from-UL Saturn/Rahu condition is a pressure indication; it does not establish separation.'),
        check('ul-seventh-dk', 'Partner and relationship context', True, 'neutral',
              'Read the seventh from UL alongside your Darakaraka’s D9 sign and their lords.',
              f'H7 from UL {seventh.value}; its lord {lord(seventh, ps).value}; DK {ks[-1]["planet"]} in D9 {dk9.value}.',
              'The seventh from UL, DK in D9 and their lords are separate relationship factors.'),
    ]
    result = module('upapada', name, 'D1', ul, conditions,
                    [fact('Selected Upapada', ul.value), fact('UL lord', lord(ul, ps).value),
                     fact('Second from UL', second.value), fact('Darakaraka', ks[-1]['planet'])])
    result['calculation'] = calculation
    result['notes'] = 'Sun is not counted as a malefic for this Upapada worksheet. This reading identifies support and pressure, without predicting a marriage count or a fixed outcome.'
    return result


def karakamsha_reading(chart: KundaliChart, ks: list[Row], basis: str) -> Row:
    ps = chart.planets if basis == 'D1' else d9_positions(chart.planets)
    anchor = Sign(ks[0]['navamsa_sign'])
    code = 'karakamsha' if basis == 'D1' else 'swamsha'
    conditions = []
    for p in ps:
        house = passed(anchor, p.sign, 1) + 1
        if house == 1:
            conditions.append(check(f'{code}-occupant-{p.planet.value}', f'{p.planet.value} · work themes', True, 'neutral',
                                    f'This placement points to themes of {OCCUPATIONS[p.planet]}.',
                                    f'{p.planet.value} occupies {anchor.value} in {basis}, H1 from the AK’s D9 sign.',
                                    f'Apply the planet-in-Karakamsha occupation rule to {basis} positions separately.'))
        if house == 10 and p.planet in (Planet.SUN, Planet.MOON, Planet.MERCURY):
            conditions.append(check(f'{code}-tenth-{p.planet.value}', 'Career direction', True, 'supportive',
                                    f'The tenth-house placement adds {OCCUPATIONS[p.planet]} to the career reading.',
                                    f'{p.planet.value} in {p.sign.value}, H10 from {anchor.value}, {basis}.',
                                    'Sun, Moon or Mercury in the tenth from Karakamsha gives the corresponding work theme.'))
        if house == 5 and p.planet in (Planet.MERCURY, Planet.JUPITER, Planet.VENUS, Planet.MOON):
            theme = 'speaking and presentation' if p.planet == Planet.VENUS else 'writing and learning'
            conditions.append(check(f'{code}-fifth-{p.planet.value}', 'Learning and expression', True, 'supportive',
                                    f'The fifth-house placement supports {theme}.',
                                    f'{p.planet.value} in {p.sign.value}, H5 from {anchor.value}, {basis}.',
                                    'Read the fifth from Karakamsha for writing, speaking and educational interests.'))
    if basis == 'D9':
        am_house = passed(anchor, Sign(ks[1]['navamsa_sign']), 1) + 1
        conditions.append(check('swamsha-amk', 'Work and education support', am_house in (1, 4, 5, 7, 9, 10, 11), 'supportive',
                                'The Amatyakaraka has a supportive D9 relationship to the Atmakaraka.',
                                f'AmK {ks[1]["planet"]}, D9 {ks[1]["navamsa_sign"]}, H{am_house} from AK in {anchor.value}.',
                                'In D9, AmK in a kendra, trine or eleventh from AK supports this condition.'))
    result = module(code, 'Karakamsha' if basis == 'D1' else 'Swamsha', basis, anchor, conditions,
                    [fact('Atmakaraka', ks[0]['planet']), fact('AK’s D9 sign', anchor.value), fact('Reading chart', basis)])
    result['houses'] = [{'house': h, 'sign': step(anchor, h - 1).value,
                         'occupants': names([p for p in ps if p.sign == step(anchor, h - 1)])} for h in range(1, 13)]
    result['notes'] = f'The anchor is the AK’s D9 sign; all occupation and house checks here use {basis} positions. Empty houses do not create a prediction by themselves.'
    return result


def yoga_reading(chart: KundaliChart, yogas: list[Row], kind: str) -> Row:
    ps = chart.planets
    by = {p.planet.value: p for p in ps}
    matches = [y for y in yogas if y['kind'] == kind and y['present']]
    groups = []
    for name in dict.fromkeys(p for y in matches for p in y['planets']):
        p = by[name]
        companions = [q for q in ps if q.sign == p.sign and q.planet != p.planet]
        conditions = [check(f'{kind}-{name}-qualified', 'Qualifying rule', True, 'supportive',
                            f'{name} meets a {kind.title()} condition in your chart.',
                            '; '.join(y['evidence'] for y in matches if name in y['planets']),
                            ' '.join(y['rule'] for y in matches if name in y['planets']))]
        if kind == 'yogada':
            for q in companions:
                theme = {Planet.JUPITER: 'teaching and study', Planet.VENUS: 'creative and relationship interests',
                         Planet.MERCURY: 'communication and analytical work', Planet.KETU: 'philosophical interests'}.get(q.planet)
                if theme:
                    conditions.append(check(f'yogada-{name}-{q.planet.value}', 'Companion influence', True, 'supportive',
                                            f'{q.planet.value} with this Yogada adds {theme}.', f'{name} and {q.planet.value} both occupy {p.sign.value} in D1.',
                                            'Interpret the specified companion planet conjunct the Yogada; a planet is not its own companion.'))
            pressure = [q for q in companions if q.planet in (Planet.MARS, Planet.RAHU, Planet.KETU)]
            conditions.append(check(f'yogada-{name}-pressure', 'Result moderation', bool(pressure), 'challenging',
                                    'The Yogada has a conjunction that can reduce or complicate its supportive results.',
                                    f'Other Mars/Rahu/Ketu companions: {names(pressure)}.',
                                    'The book’s yoga-bhanga discussion treats Mars, Rahu or Ketu conjunction as a moderating condition.'))
            second = step(p.sign, 1)
            for q in ps:
                if q.sign == second and q.planet in (Planet.SUN, Planet.MOON, Planet.MARS, Planet.MERCURY, Planet.JUPITER, Planet.VENUS):
                    theme = {Planet.SUN: 'language and computing', Planet.MOON: 'writing', Planet.MARS: 'legal work',
                             Planet.MERCURY: 'journalism', Planet.JUPITER: 'advisory responsibilities', Planet.VENUS: 'art and design'}[q.planet]
                    conditions.append(check(f'yogada-{name}-second-{q.planet.value}', 'Skills and expression', True, 'supportive',
                                            f'{q.planet.value} in the second from this Yogada points to {theme}.',
                                            f'{q.planet.value} in {second.value}, H2 from {name} in {p.sign.value}.',
                                            'Apply the named second-from-Yogada planet rule to actual D1 occupation.'))
        else:
            pressure = [q for q in companions if q.planet in MALEFICS]
            conditions.append(check(f'kevala-{name}-pressure', 'Companion pressure', bool(pressure), 'challenging',
                                    'A malefic companion can complicate this Kevala planet’s supportive result.',
                                    f'Other Sun/Mars/Saturn/Rahu/Ketu companions: {names(pressure)}.',
                                    'A malefic conjunct the Kevala modifies its result. Exclude the Kevala planet itself.'))
        groups.append({'planet': name, 'sign': p.sign.value, **assess(conditions)})
    result = module(kind, f'{kind.title()} planet predictions', 'D1', chart.ascendant.sign,
                    [c for g in groups for c in g['conditions']], [fact('Qualifying planets', ', '.join(g['planet'] for g in groups) or 'None')])
    result['groups'] = groups
    return result


def dasha_readings(chart: KundaliChart, ks: list[Row], systems: list[Row]) -> None:
    """A result rule is scoped to its documented method, never all 38 timelines."""
    by = {p.planet: p for p in chart.planets}
    for system in systems:
        system['predictions'] = {}
        for sign in Sign:
            conditions = []
            for existing in system['activation_rules'].get(sign.value, []):
                tone = 'supportive' if existing['topic'] in ('Money & comforts', 'Work support') else 'neutral'
                conditions.append({**existing, 'code': f'{system["code"]}-{existing["topic"]}', 'tone': tone})
            if system['code'] == 'chara':
                good = sign in (Sign.TAURUS, Sign.CANCER, Sign.LIBRA, Sign.GEMINI, Sign.VIRGO, Sign.SAGITTARIUS, Sign.PISCES)
                conditions.extend([
                    check('chara-sign-support', 'Sign’s general tendency', good, 'supportive', 'This is a supportive sign in the Chara chapter’s general classification.', sign.value, 'Chara classifies Taurus, Cancer, Libra, Gemini, Virgo, Sagittarius and Pisces as supportive signs.'),
                    check('chara-sign-pressure', 'Sign’s general tendency', not good, 'challenging', 'This sign has a challenging general tendency in the Chara chapter.', sign.value, 'The Chara chapter flags Aries, Leo, Scorpio, Capricorn and Aquarius as difficult signs.'),
                    check('chara-ak', 'Atmakaraka period', sign == by[Planet(ks[0]['planet'])].sign, 'mixed', 'The AK’s occupied sign has mixed results in this method.', f'AK {ks[0]["planet"]} in {ks[0]["sign"]}; period {sign.value}.', 'The Chara chapter describes mixed results for the AK’s occupied sign.'),
                    check('chara-rahu', 'Rahu occupation', sign == by[Planet.RAHU].sign, 'challenging', 'Rahu occupation adds a caution about resources and stability.', f'Rahu {by[Planet.RAHU].sign.value}; period {sign.value}.', 'Evaluate Rahu occupying the running Chara sign; no adverse event is inferred from this alone.'),
                    check('chara-ketu', 'Ketu occupation', sign == by[Planet.KETU].sign, 'supportive', 'Ketu occupation adds the Chara chapter’s supportive exception.', f'Ketu {by[Planet.KETU].sign.value}; period {sign.value}.', 'Ketu is treated as supportive in Chara; this exception is not applied to other methods.'),
                ])
            elif system['code'] == 'navamsa':
                conditions.append(check('navamsa-leo-sagittarius', 'D9 sign caution', sign in (Sign.LEO, Sign.SAGITTARIUS), 'challenging',
                                        'The Navamsa chapter flags this sign as a difficult period.', f'D9 period sign {sign.value}.',
                                        'Leo and Sagittarius are cautioned in the Navamsa chapter, including their subperiods.'))
            elif system['code'] in ('trikona', 'gochara'):
                ps = chart.planets
                owner = by[lord(sign, ps)]
                occupants = [p for p in ps if p.sign == sign]
                support = [p for p in occupants if p.planet in benefics(ps, ps)]
                conditions.extend([
                    check('trikona-benefic-occupant', 'Benefic occupation', bool(support), 'supportive', 'A benefic occupies this period sign, supporting its result.', f'{sign.value}: {names(support)}.', 'The Trikona/Gochara result discussion evaluates benefic occupation of the running sign.'),
                    check('trikona-lord-exalted', 'Sign lord’s strength', exalted(owner), 'supportive', 'The period sign’s lord is exalted, a supportive strength condition.', f'{owner.planet.value} in {owner.sign.value}.', 'An exalted period-sign lord supports the result; use the declared co-lord convention.'),
                    check('trikona-lord-debilitated', 'Sign lord’s weakness', DEBILITATION_SIGN.get(owner.planet) == owner.sign, 'challenging', 'The period sign’s lord is debilitated, indicating more difficulty.', f'{owner.planet.value} in {owner.sign.value}.', 'A debilitated period-sign lord is a challenging condition. Disputed node debilitation is not invented.'),
                ])
            result = assess(conditions)
            result['basis'] = system['basis']
            result['scope'] = ('Method-specific natal conditions; conjunctions and house relationships use the stated reading chart.' if conditions else
                               'No verified good/bad result rule is applied to this method. Its dates and chart connections remain available.')
            if system['code'] == 'gochara':
                result['scope'] += ' Transit-dependent conditions are not evaluated.'
            system['predictions'][sign.value] = result


def build_detailed_predictions(chart: KundaliChart, ks: list[Row], padas: list[Row], yogas: list[Row], variants: list[Row], systems: list[Row]) -> Row:
    ul_readings = [upapada_reading(chart, ks, Sign(padas[-1]['sign']), 'Standard Upapada', padas[-1]['calculation'])]
    ul_readings += [upapada_reading(chart, ks, Sign(v['sign']), v['name'], v['calculation']) for v in variants]
    dasha_readings(chart, ks, systems)
    return {'modules': [arudha_reading(chart, padas), ul_readings[0], karakamsha_reading(chart, ks, 'D1'),
                        karakamsha_reading(chart, ks, 'D9'), yoga_reading(chart, yogas, 'yogada'), yoga_reading(chart, yogas, 'kevala')],
            'upapada_readings': ul_readings,
            'assessment_rule': 'Support only → supportive; pressure only → challenging; both or an explicit mixed rule → mixed. No matching directional rule → no clear indication. Conditions are not added into a numerical score.'}
