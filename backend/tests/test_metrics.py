from datetime import date, datetime, timezone

import pytest

from app.schemas.records import ComparisonObservation
from app.services.metrics import calculate_metrics


def observation(
    forecast: float | None,
    actual: float | None,
    availability: str | None = None,
) -> ComparisonObservation:
    resolved_availability = availability or (
        "matched" if forecast is not None and actual is not None
        else "missing_forecast" if forecast is None and actual is not None
        else "missing_actual" if forecast is not None and actual is None
        else "missing_both"
    )
    return ComparisonObservation(
        decision_date=date(2026, 1, 1),
        delivery_date=date(2026, 1, 2),
        decision_cutoff=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        target_time=datetime(2026, 1, 2, 0, tzinfo=timezone.utc),
        forecast_publish_time=datetime(2026, 1, 1, 11, tzinfo=timezone.utc) if forecast is not None else None,
        forecast_mw=forecast,
        actual_mw=actual,
        forecast_age_minutes=60 if forecast is not None else None,
        availability=resolved_availability,
    )


def test_calculates_error_metrics_coverage_and_missing_counts() -> None:
    metrics = calculate_metrics([
        observation(12, 10),
        observation(7, 9),
        observation(None, 0),
        observation(5, None),
        observation(None, None),
    ])

    assert metrics.observation_count == 5
    assert metrics.matched_observations == 2
    assert metrics.missing_forecasts == 2
    assert metrics.missing_actuals == 2
    assert metrics.forecast_coverage_pct == 60
    assert metrics.actual_coverage_pct == 60
    assert metrics.mae_mw == 2
    assert metrics.rmse_mw == 2
    assert metrics.mean_bias_error_mw == 0
    assert metrics.wape_pct == pytest.approx(4 / 19 * 100)
    assert metrics.maximum_absolute_error_mw == 2
    assert metrics.mean_forecast_mw == pytest.approx(8)
    assert metrics.mean_actual_mw == pytest.approx(19 / 3)


def test_zero_actual_magnitude_yields_undefined_wape() -> None:
    metrics = calculate_metrics([observation(4, 0)])

    assert metrics.mae_mw == 4
    assert metrics.wape_pct is None


def test_empty_and_unmatched_observations_do_not_invent_metrics() -> None:
    empty = calculate_metrics([])
    unmatched = calculate_metrics([observation(None, 0)])

    assert empty.observation_count == 0
    assert empty.forecast_coverage_pct is None
    assert empty.mae_mw is None
    assert empty.wape_pct is None
    assert unmatched.matched_observations == 0
    assert unmatched.mae_mw is None
    assert unmatched.wape_pct is None
