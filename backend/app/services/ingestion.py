import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.clients.elexon import ElexonClient
from app.schemas.records import ActualRecord, ForecastRecord
from app.services.normalization import normalize_actual, normalize_forecast

logger = logging.getLogger(__name__)


class IngestionResult:
    def __init__(self) -> None:
        self.forecasts: list[ForecastRecord] = []
        self.actuals: list[ActualRecord] = []
        self.invalid_forecasts = 0
        self.invalid_actuals = 0
        self.raw_forecast_count = 0
        self.raw_actual_count = 0


def _normalize_records(
    records: list[dict[str, Any]],
    normalizer: Any,
) -> tuple[list[Any], int]:
    normalized = []
    invalid = 0
    for record in records:
        try:
            normalized.append(normalizer(record))
        except (ValueError, TypeError, KeyError) as error:
            invalid += 1
            logger.warning("Skipping malformed Elexon record: %s", error)
    return normalized, invalid


async def load_january_comparison_inputs(
    client: ElexonClient,
    decision_start: date,
    decision_end: date,
    cutoff_local_time: time,
    forecast_lookback_days: int,
) -> IngestionResult:
    if decision_end < decision_start:
        raise ValueError("decision_end must be on or after decision_start.")
    result = IngestionResult()
    delivery_start = decision_start + timedelta(days=1)
    delivery_end = decision_end + timedelta(days=1)
    raw_actuals = await client.fetch_actuals(delivery_start, delivery_end)
    result.raw_actual_count = len(raw_actuals)
    result.actuals, result.invalid_actuals = _normalize_records(raw_actuals, normalize_actual)

    latest_cutoff = datetime.combine(
        decision_end,
        cutoff_local_time,
        tzinfo=ZoneInfo("Europe/London"),
    )
    first_publication = datetime.combine(
        decision_start - timedelta(days=forecast_lookback_days),
        time.min,
        tzinfo=ZoneInfo("Europe/London"),
    )
    raw_forecasts = await client.fetch_forecasts(
        first_publication.astimezone(timezone.utc),
        latest_cutoff.astimezone(timezone.utc),
    )
    result.raw_forecast_count = len(raw_forecasts)
    result.forecasts, result.invalid_forecasts = _normalize_records(
        raw_forecasts, normalize_forecast
    )
    return result
