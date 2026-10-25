import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.clients.elexon import ElexonAPIError, ElexonClient
from app.schemas.records import ActualRecord, ForecastRecord
from app.services.ingestion_store import IngestionStore
from app.services.normalization import normalize_actual, normalize_forecast
from app.services.point_in_time import expected_delivery_intervals, to_utc

logger = logging.getLogger(__name__)
LONDON = ZoneInfo("Europe/London")


def _normalize_batch(
    dataset: str,
    records: list[dict[str, Any]],
    normalizer,
) -> tuple[list[Any], list[dict[str, Any]]]:
    valid = []
    rejected = []
    for record in records:
        try:
            valid.append(normalizer(record))
        except (ValueError, TypeError, KeyError) as error:
            rejected.append({
                "dataset": dataset,
                "error": str(error),
                "source_record": record,
            })
            logger.warning("Rejecting malformed %s source record: %s", dataset, error)
    return valid, rejected


def _conflict_counts(
    records: list[ForecastRecord] | list[ActualRecord],
    forecast: bool,
) -> tuple[int, int]:
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for record in records:
        key: tuple = (to_utc(record.start_time),)
        if forecast:
            assert isinstance(record, ForecastRecord)
            key += (to_utc(record.publish_time),)
        grouped[key].append(record.generation_mw)
    duplicate_groups = sum(len(values) > 1 for values in grouped.values())
    conflicting_groups = sum(len(set(values)) > 1 for values in grouped.values())
    return duplicate_groups, conflicting_groups


def _off_grid_forecasts(records: list[ForecastRecord]) -> int:
    return sum(
        record.start_time.second != 0
        or record.start_time.microsecond != 0
        or record.start_time.minute not in (0, 30)
        for record in records
    )


def _missing_actual_intervals(
    actuals: list[ActualRecord],
    start_date: date,
    end_date: date,
) -> int:
    actual_targets = {to_utc(record.start_time) for record in actuals}
    missing = 0
    current = start_date
    while current <= end_date:
        expected = expected_delivery_intervals(current)
        missing += sum(target not in actual_targets for target in expected)
        current += timedelta(days=1)
    return missing


async def run_incremental_ingestion(
    client: ElexonClient,
    store: IngestionStore,
    lookback_days: int,
    forecast_overlap_hours: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    if lookback_days < 1 or forecast_overlap_hours < 1:
        raise ValueError("Ingestion lookback and forecast overlap must be positive.")
    now_utc = to_utc(now or datetime.now(timezone.utc))
    started_at = datetime.now(timezone.utc)
    run: dict[str, Any] = {
        "run_id": str(uuid4()),
        "status": "running",
        "started_at": started_at.isoformat(),
        "finished_at": None,
        "forecast_records_retrieved": 0,
        "actual_records_retrieved": 0,
        "forecast_records_valid": 0,
        "actual_records_valid": 0,
        "rejected_records": 0,
        "invalid_forecast_records": 0,
        "invalid_actual_records": 0,
        "forecast_source_latest_time": None,
        "actual_source_latest_time": None,
        "duplicate_forecast_groups": 0,
        "duplicate_actual_groups": 0,
        "conflicting_forecast_groups": 0,
        "conflicting_actual_groups": 0,
        "off_grid_forecast_records": 0,
        "missing_actual_intervals": 0,
        "failed_requests": 0,
        "error": None,
    }
    failures_before = client.failed_requests
    today_london = now_utc.astimezone(LONDON).date()
    actual_start = today_london - timedelta(days=lookback_days - 1)
    actual_end = today_london
    forecast_checkpoint = await store.forecast_checkpoint()
    forecast_from = (
        max(
            datetime.combine(actual_start, time.min, tzinfo=LONDON).astimezone(timezone.utc),
            forecast_checkpoint - timedelta(hours=forecast_overlap_hours),
        )
        if forecast_checkpoint is not None
        else now_utc - timedelta(days=lookback_days)
    )

    try:
        raw_actuals = await client.fetch_actuals(actual_start, actual_end)
        raw_forecasts = await client.fetch_forecasts(forecast_from, now_utc)
        actuals, rejected_actuals = _normalize_batch(
            "FUELHH", raw_actuals, normalize_actual
        )
        forecasts, rejected_forecasts = _normalize_batch(
            "WINDFOR", raw_forecasts, normalize_forecast
        )
        rejected = rejected_actuals + rejected_forecasts
        added = await store.merge_records(
            forecasts=raw_forecasts,
            actuals=raw_actuals,
            rejected=rejected,
        )

        run.update(
            status="succeeded",
            finished_at=datetime.now(timezone.utc).isoformat(),
            forecast_records_retrieved=len(raw_forecasts),
            actual_records_retrieved=len(raw_actuals),
            forecast_records_valid=len(forecasts),
            actual_records_valid=len(actuals),
            rejected_records=len(rejected),
            invalid_forecast_records=len(rejected_forecasts),
            invalid_actual_records=len(rejected_actuals),
            duplicate_forecast_records=added["forecasts_duplicates"],
            duplicate_actual_records=added["actuals_duplicates"],
            forecast_records_added=added["forecasts_added"],
            actual_records_added=added["actuals_added"],
            duplicate_forecast_groups=_conflict_counts(forecasts, True)[0],
            duplicate_actual_groups=_conflict_counts(actuals, False)[0],
            conflicting_forecast_groups=_conflict_counts(forecasts, True)[1],
            conflicting_actual_groups=_conflict_counts(actuals, False)[1],
            off_grid_forecast_records=_off_grid_forecasts(forecasts),
            missing_actual_intervals=_missing_actual_intervals(
                actuals, actual_start, actual_end
            ),
            forecast_source_latest_time=max(
                (to_utc(record.publish_time) for record in forecasts), default=None
            ),
            actual_source_latest_time=max(
                (to_utc(record.start_time) for record in actuals), default=None
            ),
            failed_requests=client.failed_requests - failures_before,
        )
        await store.save_run(run, checkpoint=now_utc)
        return run
    except Exception as error:
        run.update(
            status="failed",
            error=str(error),
            failed_requests=client.failed_requests - failures_before,
        )
        await store.record_failed_run(run)
        logger.exception("Elexon ingestion run %s failed", run["run_id"])
        raise
