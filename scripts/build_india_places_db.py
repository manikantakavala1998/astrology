"""One-time build script: converts GeoNames' raw India dump into a compact,
indexed SQLite database bundled with the app (src/vedic_astro/data/india_places.db).

Run once during development, not at app runtime - the resulting .db file is
what ships with the app and is read entirely offline. Source data:
  https://download.geonames.org/export/dump/IN.zip
  https://download.geonames.org/export/dump/admin1CodesASCII.txt
(both public domain / CC-BY 4.0, GeoNames gazetteer)

Usage: python scripts/build_india_places_db.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent.parent / "build_data"
OUT_PATH = Path(__file__).resolve().parent.parent / "src" / "vedic_astro" / "data" / "india_places.db"

GEONAMES_COLUMNS = [
    "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
    "feature_class", "feature_code", "country_code", "cc2", "admin1_code",
    "admin2_code", "admin3_code", "admin4_code", "population", "elevation",
    "dem", "timezone", "modification_date",
]


def load_admin1_names() -> dict[str, str]:
    """"IN.<code>" -> state/UT name, from the small admin1CodesASCII.txt reference file."""
    mapping: dict[str, str] = {}
    path = BUILD_DIR / "admin1CodesASCII.txt"
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            code, name = parts[0], parts[1]
            if code.startswith("IN."):
                mapping[code] = name
    return mapping


def build() -> None:
    admin1_names = load_admin1_names()
    print(f"Loaded {len(admin1_names)} India admin1 (state) names")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUT_PATH.exists():
        OUT_PATH.unlink()

    conn = sqlite3.connect(OUT_PATH)
    conn.execute(
        """
        CREATE TABLE places (
            geonameid INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            state TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            population INTEGER NOT NULL,
            timezone TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE places_fts USING fts5(
            name, alternatenames, content='places', content_rowid='geonameid'
        )
        """
    )

    in_path = BUILD_DIR / "IN.txt"
    kept = 0
    skipped_no_state = 0
    batch: list[tuple[object, ...]] = []
    fts_batch: list[tuple[object, ...]] = []

    with in_path.open(encoding="utf-8") as f:
        for line in f:
            fields = line.rstrip("\n").split("\t")
            if len(fields) != len(GEONAMES_COLUMNS):
                continue
            row = dict(zip(GEONAMES_COLUMNS, fields))
            if row["feature_class"] != "P":
                continue

            admin1_code = f"IN.{row['admin1_code']}" if row["admin1_code"] else ""
            state = admin1_names.get(admin1_code, "")
            if not state:
                skipped_no_state += 1
                continue

            geonameid = int(row["geonameid"])
            name = row["name"]
            alternatenames = row["alternatenames"].replace(",", " ")
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
            population = int(row["population"]) if row["population"] else 0
            timezone = row["timezone"] or "Asia/Kolkata"

            batch.append((geonameid, name, state, latitude, longitude, population, timezone))
            fts_batch.append((geonameid, name, alternatenames))
            kept += 1

            if len(batch) >= 20000:
                conn.executemany("INSERT INTO places VALUES (?,?,?,?,?,?,?)", batch)
                conn.executemany(
                    "INSERT INTO places_fts (rowid, name, alternatenames) VALUES (?,?,?)", fts_batch
                )
                batch.clear()
                fts_batch.clear()

    if batch:
        conn.executemany("INSERT INTO places VALUES (?,?,?,?,?,?,?)", batch)
        conn.executemany(
            "INSERT INTO places_fts (rowid, name, alternatenames) VALUES (?,?,?)", fts_batch
        )
        conn.commit()

    conn.execute("CREATE INDEX idx_places_population ON places(population DESC)")
    conn.commit()
    conn.execute("VACUUM")
    conn.close()

    print(f"Kept {kept} populated places, skipped {skipped_no_state} with no resolvable state")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1_048_576:.1f} MB)")


if __name__ == "__main__":
    build()
