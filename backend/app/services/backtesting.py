from datetime import date, datetime, time, timedelta
from typing import Callable, Iterable

from app.schemas.analysis import (
    AccuracyMetrics,
    BacktestCommonResult,
    BacktestCutoffResult,
    BacktestResponse,
)
from app.schemas.records import ActualRecord, ComparisonObservation, ForecastRecord
from app.services.metrics import calculate_metrics
from app.services.point_in_time import (
    expected_delivery_intervals,
    select_latest_forecast,
    select_point_in_time,
    to_utc,
)


def _persistence_values(
    observations: list[ComparisonObservation],
    forecasts: list[ForecastRecord],
) -> dict[datetime, float]:
    forecasts_by_target: dict[datetime, list[ForecastRecord]] = {}
    for forecast in forecasts:
        forecasts_by_target.setdefault(to_utc(forecast.start_time), []).append(forecast)

    baseline: dict[datetime, float] = {}
    for observation in observations:
        previous_target = observation.target_time - timedelta(minutes=30)
        if previous_target not in expected_delivery_intervals(observation.delivery_date):
            continue
        previous_forecast, _ = select_latest_forecast(
            forecasts_by_target.get(previous_target, []), observation.decision_cutoff
        )
        if previous_forecast is not None:
            baseline[observation.target_time] = previous_forecast.generation_mw
    return baseline


def _matched_rows(
    observations: list[ComparisonObservation],
    predicate: Callable[[ComparisonObservation], bool],
) -> list[ComparisonObservation]:
    return [
        row for row in observations
        if row.actual_mw is not None and predicate(row)
    ]


def _metrics_for_values(
    observations: list[ComparisonObservation],
    values: dict[datetime, float],
) -> AccuracyMetrics:
    rows = _matched_rows(observations, lambda row: row.target_time in values)
    synthetic = [
        row.model_copy(
            update={
                "forecast_mw": values[row.target_time],
                "error_mw": values[row.target_time] - row.actual_mw,
            }
        )
        for row in rows
    ]
    return calculate_metrics(synthetic)


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _error_quantiles(
    observations: list[ComparisonObservation],
) -> dict[str, float] | None:
    errors = [
        row.forecast_mw - row.actual_mw
        for row in observations
        if row.forecast_mw is not None and row.actual_mw is not None
    ]
    if not errors:
        return None
    return {
        "p10": _quantile(errors, 0.1),
        "p50": _quantile(errors, 0.5),
        "p90": _quantile(errors, 0.9),
    }


def run_backtest(
    decision_dates: Iterable[date],
    forecasts: list[ForecastRecord],
    actuals: Iterable[ActualRecord],
    first_cutoff: time,
    second_cutoff: time,
) -> BacktestResponse:
    dates = sorted(set(decision_dates))
    if not dates:
        raise ValueError("At least one decision date is required.")
    first_rows = select_point_in_time(dates, forecasts, actuals, first_cutoff)
    second_rows = select_point_in_time(dates, forecasts, actuals, second_cutoff)
    first_by_target = {row.target_time: row for row in first_rows}
    second_by_target = {row.target_time: row for row in second_rows}

    first_matched = _matched_rows(first_rows, lambda row: row.forecast_mw is not None)
    second_matched = _matched_rows(second_rows, lambda row: row.forecast_mw is not None)
    first_baseline = _persistence_values(first_rows, forecasts)
    second_baseline = _persistence_values(second_rows, forecasts)

    common_targets = {
        target
        for target in first_by_target.keys() & second_by_target.keys()
        if first_by_target[target].actual_mw is not None
        and first_by_target[target].forecast_mw is not None
        and second_by_target[target].forecast_mw is not None
    }
    common_first = [first_by_target[target] for target in sorted(common_targets)]
    common_second = [second_by_target[target] for target in sorted(common_targets)]

    first_baseline_rows = _matched_rows(
        first_rows,
        lambda row: row.target_time in first_baseline and row.forecast_mw is not None,
    )
    second_baseline_rows = _matched_rows(
        second_rows,
        lambda row: row.target_time in second_baseline and row.forecast_mw is not None,
    )
    first_mw = [
        row.forecast_mw for row in first_matched if row.forecast_mw is not None
    ]

    return BacktestResponse(
        decision_start=dates[0],
        decision_end=dates[-1],
        timezone="Europe/London",
        first=BacktestCutoffResult(
            cutoff_local_time=first_cutoff,
            forecast_metrics=calculate_metrics(first_matched),
            benchmark_forecast_metrics=_metrics_for_values(
                first_baseline_rows,
                {
                    row.target_time: row.forecast_mw
                    for row in first_baseline_rows
                    if row.forecast_mw is not None
                },
            ),
            persistence_metrics=_metrics_for_values(first_baseline_rows, first_baseline),
            persistence_matched_observations=len(first_baseline_rows),
        ),
        second=BacktestCutoffResult(
            cutoff_local_time=second_cutoff,
            forecast_metrics=calculate_metrics(second_matched),
            benchmark_forecast_metrics=_metrics_for_values(
                second_baseline_rows,
                {
                    row.target_time: row.forecast_mw
                    for row in second_baseline_rows
                    if row.forecast_mw is not None
                },
            ),
            persistence_metrics=_metrics_for_values(second_baseline_rows, second_baseline),
            persistence_matched_observations=len(second_baseline_rows),
        ),
        common=BacktestCommonResult(
            matched_observations=len(common_targets),
            first_cutoff_metrics=calculate_metrics(common_first),
            second_cutoff_metrics=calculate_metrics(common_second),
        ),
        first_cutoff_error_quantiles_mw=_error_quantiles(first_matched),
        first_cutoff_mean_forecast_mw=sum(first_mw) / len(first_mw) if first_mw else None,
        first_cutoff_matched_observations=len(first_matched),
    )
