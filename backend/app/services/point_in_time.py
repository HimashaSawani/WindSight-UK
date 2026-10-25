import json
import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from app.schemas.records import ActualRecord, ComparisonObservation, ForecastRecord

LONDON = ZoneInfo("Europe/London")
UTC = timezone.utc
def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Source timestamps must include a timezone.")
    return value.astimezone(UTC)


def delivery_date_for_decision(decision_date: date) -> date:
    return decision_date + timedelta(days=1)


def decision_cutoff(decision_date: date, cutoff_local_time: time) -> datetime:
    return datetime.combine(decision_date, cutoff_local_time, tzinfo=LONDON).astimezone(UTC)


def expected_delivery_intervals(delivery_date: date) -> list[datetime]:
    local_midnight = datetime.combine(delivery_date, time.min, tzinfo=LONDON)
    start_utc = local_midnight.astimezone(UTC)
    next_midnight_utc = datetime.combine(
        delivery_date + timedelta(days=1), time.min, tzinfo=LONDON
    ).astimezone(UTC)
    interval_count = int((next_midnight_utc - start_utc).total_seconds() // 1800)
    return [start_utc + timedelta(minutes=30 * index) for index in range(interval_count)]


def _stable_key(record: ForecastRecord | ActualRecord) -> tuple[float, str]:
    generation = record.generation_mw
    if not math.isfinite(generation):
        raise ValueError("Generation must be a finite number.")
    return generation, json.dumps(
        record.source_metadata, sort_keys=True, default=str, separators=(",", ":")
    )


def select_latest_forecast(
    records: Iterable[ForecastRecord],
    cutoff: datetime,
) -> tuple[ForecastRecord | None, bool]:
    eligible = [
        record for record in records if to_utc(record.publish_time) <= to_utc(cutoff)
    ]
    if not eligible:
        return None, False
    latest_publish = max(to_utc(record.publish_time) for record in eligible)
    latest_records = [
        record for record in eligible if to_utc(record.publish_time) == latest_publish
    ]
    conflicting_duplicate = len(
        {record.generation_mw for record in latest_records}
    ) > 1
    return min(latest_records, key=_stable_key), conflicting_duplicate


def _deduplicate_actuals(
    records: Iterable[ActualRecord],
) -> tuple[dict[datetime, ActualRecord], set[datetime]]:
    grouped: dict[datetime, list[ActualRecord]] = defaultdict(list)
    for record in records:
        grouped[to_utc(record.start_time)].append(record)
    selected: dict[datetime, ActualRecord] = {}
    conflicts: set[datetime] = set()
    for target, candidates in grouped.items():
        values = {candidate.generation_mw for candidate in candidates}
        if len(values) > 1:
            conflicts.add(target)
        selected[target] = min(candidates, key=_stable_key)
    return selected, conflicts


def select_point_in_time(
    decision_dates: Iterable[date],
    forecasts: Iterable[ForecastRecord],
    actuals: Iterable[ActualRecord],
    cutoff_local_time: time,
) -> list[ComparisonObservation]:
    forecast_groups: dict[datetime, list[ForecastRecord]] = defaultdict(list)
    for forecast in forecasts:
        forecast_groups[to_utc(forecast.start_time)].append(forecast)

    actual_by_target, actual_conflicts = _deduplicate_actuals(actuals)
    observations: list[ComparisonObservation] = []

    for decision_day in sorted(set(decision_dates)):
        delivery_day = delivery_date_for_decision(decision_day)
        cutoff = decision_cutoff(decision_day, cutoff_local_time)
        for target in expected_delivery_intervals(delivery_day):
            selected, conflicting_duplicate = select_latest_forecast(
                forecast_groups.get(target, []), cutoff
            )

            actual = actual_by_target.get(target)
            if selected is None and actual is None:
                availability = "missing_both"
            elif selected is None:
                availability = "missing_forecast"
            elif actual is None:
                availability = "missing_actual"
            else:
                availability = "matched"

            published = to_utc(selected.publish_time) if selected else None
            observations.append(
                ComparisonObservation(
                    decision_date=decision_day,
                    delivery_date=delivery_day,
                    decision_cutoff=cutoff,
                    target_time=target,
                    forecast_publish_time=published,
                    forecast_mw=selected.generation_mw if selected else None,
                    actual_mw=actual.generation_mw if actual else None,
                    error_mw=(
                        selected.generation_mw - actual.generation_mw
                        if selected is not None and actual is not None
                        else None
                    ),
                    forecast_age_minutes=(
                        (cutoff - published).total_seconds() / 60 if published else None
                    ),
                    availability=availability,
                    conflicting_forecast_duplicate=conflicting_duplicate,
                    conflicting_actual_duplicate=target in actual_conflicts,
                    forecast_source_metadata=selected.source_metadata if selected else None,
                    actual_source_metadata=actual.source_metadata if actual else None,
                )
            )
    return observations
