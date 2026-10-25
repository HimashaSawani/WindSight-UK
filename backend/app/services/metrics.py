from collections.abc import Iterable
from math import sqrt

from app.schemas.analysis import AccuracyMetrics
from app.schemas.records import ComparisonObservation


def calculate_metrics(
    observations: Iterable[ComparisonObservation],
) -> AccuracyMetrics:
    rows = list(observations)
    matched = [
        row for row in rows
        if row.forecast_mw is not None and row.actual_mw is not None
    ]
    missing_forecasts = sum(row.forecast_mw is None for row in rows)
    missing_actuals = sum(row.actual_mw is None for row in rows)

    errors = [
        row.forecast_mw - row.actual_mw
        for row in matched
        if row.forecast_mw is not None and row.actual_mw is not None
    ]
    absolute_errors = [abs(error) for error in errors]
    matched_count = len(errors)
    total_count = len(rows)

    if not matched_count:
        mae = rmse = bias = wape = maximum_absolute_error = None
    else:
        mae = sum(absolute_errors) / matched_count
        rmse = sqrt(sum(error * error for error in errors) / matched_count)
        bias = sum(errors) / matched_count
        actual_magnitude = sum(
            abs(row.actual_mw)
            for row in matched
            if row.actual_mw is not None
        )
        wape = (
            sum(absolute_errors) / actual_magnitude * 100
            if actual_magnitude > 0
            else None
        )
        maximum_absolute_error = max(absolute_errors)

    return AccuracyMetrics(
        observation_count=total_count,
        matched_observations=matched_count,
        missing_forecasts=missing_forecasts,
        missing_actuals=missing_actuals,
        forecast_coverage_pct=(
            sum(row.forecast_mw is not None for row in rows) / total_count * 100
            if total_count else None
        ),
        actual_coverage_pct=(
            sum(row.actual_mw is not None for row in rows) / total_count * 100
            if total_count else None
        ),
        mean_forecast_mw=(
            sum(row.forecast_mw for row in rows if row.forecast_mw is not None)
            / sum(row.forecast_mw is not None for row in rows)
            if any(row.forecast_mw is not None for row in rows)
            else None
        ),
        mean_actual_mw=(
            sum(row.actual_mw for row in rows if row.actual_mw is not None)
            / sum(row.actual_mw is not None for row in rows)
            if any(row.actual_mw is not None for row in rows)
            else None
        ),
        mae_mw=mae,
        rmse_mw=rmse,
        mean_bias_error_mw=bias,
        wape_pct=wape,
        maximum_absolute_error_mw=maximum_absolute_error,
    )
