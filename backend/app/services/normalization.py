import math
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.schemas.records import ActualRecord, ForecastRecord

LONDON = ZoneInfo("Europe/London")


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a timestamp string.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone.")
    return parsed.astimezone(ZoneInfo("UTC"))


def _start_time(record: dict[str, Any]) -> datetime:
    value = record.get("startTime")
    if value is not None:
        return _timestamp(value, "startTime")
    settlement_date = record.get("settlementDate")
    settlement_period = record.get("settlementPeriod")
    if settlement_date is None or settlement_period is None:
        raise ValueError("Record requires startTime or settlementDate and settlementPeriod.")
    day = date.fromisoformat(str(settlement_date))
    period = int(settlement_period)
    if period < 1:
        raise ValueError("settlementPeriod must be positive.")
    local_start = datetime.combine(day, time.min, tzinfo=LONDON)
    return (local_start.astimezone(ZoneInfo("UTC")) + timedelta(minutes=30 * (period - 1)))


def _generation(record: dict[str, Any]) -> float:
    value = record.get("generation")
    if value is None or isinstance(value, bool):
        raise ValueError("generation is missing or not numeric.")
    generation = float(value)
    if not math.isfinite(generation):
        raise ValueError("generation must be finite.")
    return generation


def normalize_forecast(record: dict[str, Any]) -> ForecastRecord:
    return ForecastRecord(
        start_time=_start_time(record),
        publish_time=_timestamp(record.get("publishTime"), "publishTime"),
        generation_mw=_generation(record),
        source_metadata=dict(record),
    )


def normalize_actual(record: dict[str, Any]) -> ActualRecord:
    fuel_type = record.get("fuelType")
    if fuel_type != "WIND":
        raise ValueError("Actual record is not fuelType WIND.")
    return ActualRecord(
        start_time=_start_time(record),
        generation_mw=_generation(record),
        fuel_type="WIND",
        source_metadata=dict(record),
    )
