"""Package the public-domain 1905 edition without dropping any source text."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
TITLES = [
    "Zodiacal definitions and principles", "Planetary definitions and strengths",
    "Animal and vegetable horoscopy", "Conception", "Circumstances of birth",
    "Balarishta", "Ayurdaya", "Dashas and antardashas", "Ashtakavarga",
    "Avocation", "Raja yogas", "Nabhasa yogas", "Lunar yogas",
    "Two-planet combinations", "Ascetic yogas", "Nakshatras", "Moon in signs",
    "Planets in signs", "Planetary aspects", "Planets in bhavas", "Planets in vargas",
    "Miscellaneous yogas", "Malefic yogas", "Horoscopy of women", "Death",
    "Lost horoscopes", "Drekkanas", "Conclusion",
]


def main() -> None:
    raw = (ROOT / "docs/sources/brihat-jataka-1905.txt").read_bytes()
    text = raw.decode("utf-8")
    starts = list(re.finditer(r"^CHAPTER[^\n]+", text, re.M))
    assert len(starts) == 28
    finish = text.index("APPENDIX.", starts[-1].start())
    chapters = []
    for i, start in enumerate(starts):
        end = starts[i + 1].start() if i < 27 else finish
        body = text[start.start():end]
        chapters.append({
            "number": i + 1, "title": TITLES[i], "text": body,
            "source_line": text[:start.start()].count("\n") + 1,
            "edition_addition": i in (15, 16),
        })
    data = {
        "title": "Brihat Jataka", "author": "Varahamihira",
        "edition": "N. Chidambaram Aiyar, English translation and commentary, 1905",
        "url": "https://archive.org/details/brihatjataka00varaiala",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "notice": "Public-domain edition. Original OCR is preserved, including errors and commentary. Chapters XVI and XVII are additions identified in this edition's conclusion.",
        "front_matter": text[:starts[0].start()], "chapters": chapters,
        "appendix": text[finish:],
    }
    assert data["front_matter"] + "".join(c["text"] for c in chapters) + data["appendix"] == text
    dest = ROOT / "src/vedic_astro/data/brihat_jataka_1905.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"Packaged all 28 chapters, front matter and appendix: {dest.name}")


if __name__ == "__main__":
    main()
