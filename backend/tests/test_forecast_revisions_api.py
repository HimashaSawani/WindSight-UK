from datetime import datetime, time

from fastapi.testclient import TestClient

from app.api import data
from app.clients.elexon import ElexonClient
from app.core.config import Settings
from app.main import app


DECISION_DATE = "2026-01-01"
TARGET_TIME = "2026-01-02T00:00:00+00:00"


def raw_revision(publish_time: str, generation: float, start_time: str = TARGET_TIME) -> dict:
    return {
        "startTime": start_time,
        "publishTime": publish_time,
        "generation": generation,
    }


def request_revisions(monkeypatch, records: list[dict]) -> dict:
    async def fake_fetch_forecasts(
        self: ElexonClient, publish_from: datetime, publish_to: datetime
    ) -> list[dict]:
        assert publish_from.tzinfo is not None
        assert publish_to.tzinfo is not None
        return records

    monkeypatch.setattr(ElexonClient, "fetch_forecasts", fake_fetch_forecasts)
    monkeypatch.setattr(
        data,
        "get_settings",
        lambda: Settings(
            decision_cutoff_local_time=time(12),
            forecast_publication_lookback_days=31,
        ),
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/forecast-revisions",
            params={"decision_date": DECISION_DATE, "target_time": TARGET_TIME},
        )
    assert response.status_code == 200, response.text
    return response.json()


def test_timeline_keeps_all_revisions_and_selects_latest_at_cutoff(monkeypatch) -> None:
    result = request_revisions(
        monkeypatch,
        [
            raw_revision("2026-01-01T10:00:00Z", 100),
            raw_revision("2026-01-01T12:00:00Z", 120),
            raw_revision("2026-01-01T12:01:00Z", 999),
            raw_revision("2026-01-02T00:00:00Z", 1000, "2026-01-02T00:30:00Z"),
        ],
    )

    assert result["target_time"] == "2026-01-02T00:00:00Z"
    assert result["decision_cutoff"] == "2026-01-01T12:00:00Z"
    assert [item["generation_mw"] for item in result["revisions"]] == [100, 120, 999]
    assert [item["available_at_decision_time"] for item in result["revisions"]] == [
        True,
        True,
        False,
    ]
    assert [item["selected_for_decision"] for item in result["revisions"]] == [
        False,
        True,
        False,
    ]


def test_single_revision_is_selected(monkeypatch) -> None:
    result = request_revisions(
        monkeypatch, [raw_revision("2026-01-01T11:00:00Z", 85)]
    )

    assert len(result["revisions"]) == 1
    assert result["revisions"][0]["selected_for_decision"] is True


def test_no_matching_forecasts_returns_empty_timeline(monkeypatch) -> None:
    result = request_revisions(
        monkeypatch,
        [raw_revision("2026-01-01T11:00:00Z", 85, "2026-01-02T00:30:00Z")],
    )

    assert result["revisions"] == []


def test_duplicate_publication_timestamp_is_preserved_and_selected_stably(
    monkeypatch,
) -> None:
    result = request_revisions(
        monkeypatch,
        [
            raw_revision("2026-01-01T12:00:00Z", 100),
            raw_revision("2026-01-01T12:00:00Z", 120),
        ],
    )

    assert len(result["revisions"]) == 2
    assert [item["generation_mw"] for item in result["revisions"]] == [100, 120]
    assert all(item["duplicate_publication_timestamp"] for item in result["revisions"])
    assert all(item["conflicting_duplicate"] for item in result["revisions"])
    assert sum(item["selected_for_decision"] for item in result["revisions"]) == 1
    assert next(
        item["generation_mw"]
        for item in result["revisions"]
        if item["selected_for_decision"]
    ) == 100


def test_conflicting_duplicate_timeline_order_is_independent_of_source_order(
    monkeypatch,
) -> None:
    result = request_revisions(
        monkeypatch,
        [
            raw_revision("2026-01-01T12:00:00Z", 120),
            raw_revision("2026-01-01T12:00:00Z", 100),
        ],
    )

    assert [item["generation_mw"] for item in result["revisions"]] == [100, 120]
    assert result["revisions"][0]["selected_for_decision"] is True
    assert result["revisions"][1]["selected_for_decision"] is False


def test_london_target_and_cutoff_are_returned_as_utc(monkeypatch) -> None:
    result = request_revisions(
        monkeypatch, [raw_revision("2026-01-01T12:00:00+00:00", 85)]
    )

    assert result["timezone"] == "Europe/London"
    assert result["target_time"] == "2026-01-02T00:00:00Z"
    assert result["decision_cutoff"] == "2026-01-01T12:00:00Z"
    assert result["revisions"][0]["publish_time"] == "2026-01-01T12:00:00Z"
