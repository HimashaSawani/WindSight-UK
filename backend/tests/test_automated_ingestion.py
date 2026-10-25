from datetime import datetime, timezone

import pytest

from app.clients.elexon import ElexonAPIError
from app.services.automated_ingestion import run_incremental_ingestion
from app.services.ingestion_store import IngestionStore, acquire_ingestion_lease


class FakeClient:
    failed_requests = 0

    def __init__(self) -> None:
        self.actual_calls = []
        self.forecast_calls = []
        self.actual_records = [
            {
                "fuelType": "WIND",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 1,
                "generation": 0,
            },
            {
                "fuelType": "WIND",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 1,
                "generation": 5,
            },
            {
                "fuelType": "WIND",
                "settlementDate": "2026-01-02",
                "settlementPeriod": 2,
                "generation": "invalid",
            },
        ]
        self.forecast_records = [
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2026-01-02T10:00:00Z",
                "generation": 10,
            },
            {
                "startTime": "2026-01-02T00:00:00Z",
                "publishTime": "2026-01-02T10:00:00Z",
                "generation": 12,
            },
            {
                "startTime": "2026-01-02T00:15:00Z",
                "publishTime": "2026-01-02T10:00:00Z",
                "generation": 14,
            },
            {
                "startTime": "2026-01-02T00:30:00",
                "publishTime": "2026-01-02T10:00:00Z",
                "generation": 20,
            },
        ]

    async def fetch_actuals(self, start_date, end_date):
        self.actual_calls.append((start_date, end_date))
        return self.actual_records

    async def fetch_forecasts(self, publish_from, publish_to):
        self.forecast_calls.append((publish_from, publish_to))
        return self.forecast_records


@pytest.mark.asyncio
async def test_ingestion_validates_persists_and_preserves_conflicting_revisions(
    tmp_path,
) -> None:
    client = FakeClient()
    store = IngestionStore(str(tmp_path / "ingestion.json"))
    now = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)

    result = await run_incremental_ingestion(client, store, 2, 6, now)
    snapshot = await store.snapshot()

    assert result["status"] == "succeeded"
    assert result["actual_records_valid"] == 2
    assert result["forecast_records_valid"] == 3
    assert result["invalid_actual_records"] == 1
    assert result["invalid_forecast_records"] == 1
    assert result["duplicate_actual_groups"] == 1
    assert result["conflicting_actual_groups"] == 1
    assert result["duplicate_forecast_groups"] == 1
    assert result["conflicting_forecast_groups"] == 1
    assert result["off_grid_forecast_records"] == 1
    assert result["missing_actual_intervals"] == 48
    assert len(snapshot["forecasts"]) == 4
    assert len(snapshot["actuals"]) == 3
    assert len(snapshot["rejected"]) == 2
    assert len(snapshot["runs"]) == 1


@pytest.mark.asyncio
async def test_incremental_ingestion_is_idempotent_and_retains_revision_history(
    tmp_path,
) -> None:
    client = FakeClient()
    store = IngestionStore(str(tmp_path / "ingestion.json"))
    now = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)

    await run_incremental_ingestion(client, store, 2, 6, now)
    second = await run_incremental_ingestion(client, store, 2, 6, now)
    snapshot = await store.snapshot()

    assert second["forecast_records_added"] == 0
    assert second["actual_records_added"] == 0
    assert second["duplicate_forecast_records"] == 4
    assert second["duplicate_actual_records"] == 3
    assert len(snapshot["forecasts"]) == 4
    assert len(snapshot["runs"]) == 2
    assert await store.forecast_checkpoint() == now
    assert client.forecast_calls[1][0] == datetime(
        2026, 1, 2, 6, tzinfo=timezone.utc
    )


@pytest.mark.asyncio
async def test_failed_sync_is_recorded_and_checkpoint_does_not_advance(tmp_path) -> None:
    class FailingClient(FakeClient):
        async def fetch_actuals(self, start_date, end_date):
            self.failed_requests += 1
            raise ElexonAPIError("source timeout")

    store = IngestionStore(str(tmp_path / "ingestion.json"))
    with pytest.raises(ElexonAPIError, match="source timeout"):
        await run_incremental_ingestion(
            FailingClient(),
            store,
            2,
            6,
            datetime(2026, 1, 2, 12, tzinfo=timezone.utc),
        )

    snapshot = await store.snapshot()
    assert snapshot["runs"][0]["status"] == "failed"
    assert snapshot["runs"][0]["failed_requests"] == 1
    assert snapshot["runs"][0]["error"] == "source timeout"
    assert await store.forecast_checkpoint() is None


@pytest.mark.asyncio
async def test_corrupt_store_is_not_overwritten(tmp_path) -> None:
    store_path = tmp_path / "ingestion.json"
    store_path.write_text("{not-json", encoding="utf-8")
    store = IngestionStore(str(store_path))

    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        await store.merge_records([], [], [])

    assert store_path.read_text(encoding="utf-8") == "{not-json"


@pytest.mark.asyncio
async def test_ingestion_store_size_monitor_and_process_lease(tmp_path) -> None:
    path = tmp_path / "ingestion.json"
    store = IngestionStore(str(path))
    assert await store.size_bytes() == 0

    await store.merge_records(
        forecasts=[{"startTime": "2026-01-01T00:00:00Z", "generation": 10}],
        actuals=[],
        rejected=[],
    )
    assert await store.size_bytes() == path.stat().st_size

    lease = acquire_ingestion_lease(str(path))
    try:
        with pytest.raises(RuntimeError, match="already active"):
            acquire_ingestion_lease(str(path))
    finally:
        lease.release()

    second_lease = acquire_ingestion_lease(str(path))
    second_lease.release()
