from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from vedic_astro.dasha import DASHA_YEARS, compute_vimshottari_dasha
from vedic_astro.models import Planet
from vedic_astro.web.app import app

client = TestClient(app)


def test_branch_api_reaches_prana_with_proportional_contiguous_boundaries() -> None:
    # One genuine natal branch, through Antardasha, Pratyantara, Sookshma, Prana.
    main = compute_vimshottari_dasha(281.3945, datetime(1998, 9, 4, 0, 3)).periods[0]
    parent = main.model_dump(mode="json")
    for _ in range(4):
        response = client.post("/api/vimshottari/subperiods", json={k: parent[k] for k in ("planet", "start", "end")})
        assert response.status_code == 200
        rows = response.json()["periods"]
        assert len(rows) == 9
        assert rows[0]["planet"] == parent["planet"]
        assert rows[0]["start"] == parent["start"]
        assert rows[-1]["end"] == parent["end"]
        parent_seconds = (datetime.fromisoformat(parent["end"]) - datetime.fromisoformat(parent["start"])).total_seconds()
        for index, row in enumerate(rows):
            seconds = (datetime.fromisoformat(row["end"]) - datetime.fromisoformat(row["start"])).total_seconds()
            assert seconds > 0
            assert seconds == pytest.approx(parent_seconds * DASHA_YEARS[Planet(row["planet"])] / 120, abs=0.00001)
            assert row["sub_periods"] == []
            if index:
                assert row["start"] == rows[index - 1]["end"]
        parent = rows[3]
    assert parent_seconds < 10 * 86400  # Final request was a Sookshma period.


@pytest.mark.parametrize("start,end,status", [
    ("2000-01-01T00:00:00", "2000-01-01T00:00:00", 400),
    ("2001-01-01T00:00:00", "2000-01-01T00:00:00", 400),
    ("2000-01-01T00:00:00+05:30", "2001-01-01T00:00:00+05:30", 400),
    ("2000-01-01T00:00:00", "2200-01-01T00:00:00", 400),
    ("not-a-date", "2001-01-01T00:00:00", 422),
])
def test_branch_api_rejects_invalid_parent_intervals(start, end, status) -> None:
    assert client.post("/api/vimshottari/subperiods", json={"planet": "Sun", "start": start, "end": end}).status_code == status


def test_branch_api_rejects_a_non_vimshottari_lord() -> None:
    assert client.post("/api/vimshottari/subperiods", json={"planet": "Lagna", "start": "2000-01-01T00:00:00", "end": "2001-01-01T00:00:00"}).status_code == 422
