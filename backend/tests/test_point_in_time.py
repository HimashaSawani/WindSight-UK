from datetime import date, datetime, time, timezone

from app.schemas.records import ActualRecord, ForecastRecord
from app.services.point_in_time import (
    decision_cutoff,
    expected_delivery_intervals,
    select_point_in_time,
)


def forecast(start: str, published: str, generation: float) -> ForecastRecord:
    return ForecastRecord(
        start_time=datetime.fromisoformat(start.replace("Z", "+00:00")),
        publish_time=datetime.fromisoformat(published.replace("Z", "+00:00")),
        generation_mw=generation,
        source_metadata={"test_data": True},
    )


def actual(start: str, generation: float) -> ActualRecord:
    return ActualRecord(
        start_time=datetime.fromisoformat(start.replace("Z", "+00:00")),
        generation_mw=generation,
        fuel_type="WIND",
        source_metadata={"test_data": True},
    )


def test_selects_latest_forecast_at_or_before_cutoff_only() -> None:
    target = "2026-01-02T00:00:00Z"
    forecasts = [
        forecast(target, "2025-12-31T10:00:00Z", 100),
        forecast(target, "2026-01-01T11:59:00Z", 120),
        forecast(target, "2026-01-01T12:01:00Z", 999),
    ]

    result = select_point_in_time(
        [date(2026, 1, 1)],
        forecasts,
        [actual(target, 110)],
        time(12),
    )

    first = result[0]
    assert first.forecast_mw == 120
    assert first.forecast_publish_time == datetime(2026, 1, 1, 11, 59, tzinfo=timezone.utc)
    assert first.actual_mw == 110
    assert first.availability == "matched"
    assert first.forecast_age_minutes == 1


def test_no_eligible_forecast_is_explicit() -> None:
    result = select_point_in_time(
        [date(2026, 1, 1)],
        [forecast("2026-01-02T00:00:00Z", "2026-01-01T12:01:00Z", 100)],
        [],
        time(12),
    )

    assert result[0].availability == "missing_both"
    assert result[0].forecast_mw is None
    assert result[0].actual_mw is None


def test_missing_actual_is_explicit() -> None:
    result = select_point_in_time(
        [date(2026, 1, 1)],
        [forecast("2026-01-02T00:00:00Z", "2026-01-01T10:00:00Z", 100)],
        [],
        time(12),
    )

    assert result[0].availability == "missing_actual"
    assert result[0].actual_mw is None


def test_equal_latest_publications_choose_deterministically_and_flag_conflict() -> None:
    target = "2026-01-02T00:00:00Z"
    result = select_point_in_time(
        [date(2026, 1, 1)],
        [
            forecast(target, "2026-01-01T10:00:00Z", 120),
            forecast(target, "2026-01-01T10:00:00Z", 100),
        ],
        [],
        time(12),
    )

    assert result[0].forecast_mw == 100
    assert result[0].conflicting_forecast_duplicate is True


def test_conflicting_actual_duplicates_are_flagged_and_resolved_stably() -> None:
    target = "2026-01-02T00:00:00Z"
    result = select_point_in_time(
        [date(2026, 1, 1)],
        [forecast(target, "2026-01-01T10:00:00Z", 100)],
        [actual(target, 110), actual(target, 90)],
        time(12),
    )

    assert result[0].actual_mw == 90
    assert result[0].conflicting_actual_duplicate is True


def test_january_31_decision_delivers_february_1_and_full_48_intervals() -> None:
    result = select_point_in_time([date(2026, 1, 31)], [], [], time(12))

    assert len(result) == 48
    assert result[0].decision_date == date(2026, 1, 31)
    assert result[0].delivery_date == date(2026, 2, 1)
    assert result[-1].target_time == datetime(2026, 2, 1, 23, 30, tzinfo=timezone.utc)


def test_london_cutoff_is_converted_to_utc_and_dst_interval_count_is_correct() -> None:
    assert decision_cutoff(date(2026, 1, 31), time(12)) == datetime(
        2026, 1, 31, 12, tzinfo=timezone.utc
    )
    assert len(expected_delivery_intervals(date(2026, 3, 29))) == 46
    assert len(expected_delivery_intervals(date(2026, 10, 25))) == 50
