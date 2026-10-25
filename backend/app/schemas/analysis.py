from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel

from app.schemas.records import ComparisonObservation


class AccuracyMetrics(BaseModel):
    observation_count: int
    matched_observations: int
    missing_forecasts: int
    missing_actuals: int
    forecast_coverage_pct: float | None
    actual_coverage_pct: float | None
    mean_forecast_mw: float | None
    mean_actual_mw: float | None
    mae_mw: float | None
    rmse_mw: float | None
    mean_bias_error_mw: float | None
    wape_pct: float | None
    maximum_absolute_error_mw: float | None


class DailyAccuracy(BaseModel):
    decision_date: date
    delivery_date: date
    metrics: AccuracyMetrics


class ComparisonResponse(BaseModel):
    decision_cutoff_local_time: time
    timezone: Literal["Europe/London"]
    decision_dates: list[date]
    observation_count: int
    observations: list[ComparisonObservation]


class ForecastRevision(BaseModel):
    publish_time: datetime
    generation_mw: float
    available_at_decision_time: bool
    selected_for_decision: bool
    duplicate_publication_timestamp: bool
    conflicting_duplicate: bool


class ForecastRevisionResponse(BaseModel):
    decision_date: date
    delivery_date: date
    target_time: datetime
    decision_cutoff: datetime
    decision_cutoff_local_time: time
    timezone: Literal["Europe/London"]
    revisions: list[ForecastRevision]


class AccuracyResponse(BaseModel):
    decision_cutoff_local_time: time
    timezone: Literal["Europe/London"]
    decision_start: date
    decision_end: date
    by_decision_date: list[DailyAccuracy]
    by_delivery_date: list[DailyAccuracy]
    overall: AccuracyMetrics


class HistoryResponse(BaseModel):
    decision_cutoff_local_time: time
    timezone: Literal["Europe/London"]
    decision_start: date
    decision_end: date
    days: list[DailyAccuracy]


class OverviewResponse(BaseModel):
    decision_cutoff_local_time: time
    timezone: Literal["Europe/London"]
    decision_start: date
    decision_end: date
    generated_at: datetime
    metrics: AccuracyMetrics
    daily_history: list[DailyAccuracy]
