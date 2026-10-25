import logging
import asyncio
import hmac
import time as monotonic_time
from datetime import date, datetime, time, timedelta, timezone
from math import ceil
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.clients.elexon import ElexonAPIError
from app.core.config import get_settings
from app.schemas.analysis import (
    APIPerformanceResponse,
    AccuracyResponse,
    BacktestResponse,
    DailyAccuracy,
    ForecastRevision,
    ForecastRevisionResponse,
    HistoryResponse,
    OverviewResponse,
    ComparisonResponse,
)
from app.schemas.records import ActualRecord, ComparisonObservation, ForecastRecord
from app.services.automated_ingestion import run_incremental_ingestion
from app.services.ingestion import load_january_comparison_inputs
from app.services.backtesting import run_backtest
from app.services.metrics import calculate_metrics
from app.services.normalization import normalize_actual, normalize_forecast
from app.services.point_in_time import (
    decision_cutoff,
    expected_delivery_intervals,
    select_latest_forecast,
    select_point_in_time,
    to_utc,
)

router = APIRouter()
logger = logging.getLogger(__name__)
JANUARY_START = date(2026, 1, 1)
JANUARY_END = date(2026, 1, 31)


class ActualDatasetResponse(BaseModel):
    dataset: str
    record_count: int
    records: list[ActualRecord]


class ForecastDatasetResponse(BaseModel):
    dataset: str
    record_count: int
    records: list[ForecastRecord]


class DataDiagnosticsResponse(BaseModel):
    analytics_data_source: Literal["live_elexon"]
    status: str
    last_operation: str | None
    last_attempt: datetime | None
    last_successful_refresh: datetime | None
    raw_forecast_records: int
    normalized_forecast_records: int
    invalid_forecast_records: int
    raw_actual_records: int
    normalized_actual_records: int
    invalid_actual_records: int
    requests_made: int
    cache_hits: int
    failed_requests: int
    missing_forecast_records: int
    missing_actual_records: int
    forecast_source_latest_time: datetime | None
    actual_source_latest_time: datetime | None
    ingestion_enabled: bool
    stored_forecast_records: int
    stored_actual_records: int
    stored_rejected_records: int
    recent_ingestion_runs: list[dict[str, Any]]
    missing_actual_intervals: int
    duplicate_forecast_records: int
    duplicate_actual_records: int
    conflicting_forecast_groups: int
    conflicting_actual_groups: int
    off_grid_forecast_records: int
    message: str


def _diagnostics(request: Request) -> dict[str, Any]:
    if not hasattr(request.app.state, "data_diagnostics"):
        request.app.state.data_diagnostics = {
            "status": "not_requested",
            "last_operation": None,
            "last_attempt": None,
            "last_successful_refresh": None,
            "raw_forecast_records": 0,
            "normalized_forecast_records": 0,
            "invalid_forecast_records": 0,
            "raw_actual_records": 0,
            "normalized_actual_records": 0,
            "invalid_actual_records": 0,
            "missing_forecast_records": 0,
            "missing_actual_records": 0,
            "forecast_source_latest_time": None,
            "actual_source_latest_time": None,
            "message": "No Elexon data has been requested in this process.",
        }
    return request.app.state.data_diagnostics


def _normalise(
    records: list[dict[str, Any]], normalizer: Any
) -> tuple[list[Any], int]:
    output: list[Any] = []
    invalid = 0
    for record in records:
        try:
            output.append(normalizer(record))
        except (ValueError, TypeError, KeyError) as error:
            invalid += 1
            logger.warning("Skipping malformed Elexon record: %s", error)
    return output, invalid


async def _load_observations(
    request: Request, decision_start: date, decision_end: date
) -> tuple[list[ComparisonObservation], Any]:
    settings = get_settings()
    diagnostics = _diagnostics(request)
    cache_key = (
        decision_start,
        decision_end,
        settings.decision_cutoff_local_time,
        settings.forecast_publication_lookback_days,
    )
    async with request.app.state.analysis_lock:
        cached = request.app.state.analysis_cache.get(cache_key)
        if cached is not None and cached[0] > monotonic_time.monotonic():
            return cached[1], settings
        task = request.app.state.analysis_inflight.get(cache_key)
        if task is None:
            task = asyncio.create_task(
                _fetch_and_select(request, decision_start, decision_end, settings)
            )
            request.app.state.analysis_inflight[cache_key] = task
    try:
        observations = await task
    except ElexonAPIError as error:
        diagnostics.update(status="error", last_operation="comparison", message=str(error))
        raise HTTPException(
            status_code=502,
            detail={"code": "elexon_error", "message": str(error)},
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_decision_range", "message": str(error)},
        ) from error
    finally:
        if task.done():
            async with request.app.state.analysis_lock:
                if request.app.state.analysis_inflight.get(cache_key) is task:
                    request.app.state.analysis_inflight.pop(cache_key, None)
    async with request.app.state.analysis_lock:
        request.app.state.analysis_cache[cache_key] = (
            monotonic_time.monotonic() + 30,
            observations,
        )
    return observations, settings


async def _fetch_and_select(
    request: Request,
    decision_start: date,
    decision_end: date,
    settings: Any,
) -> list[ComparisonObservation]:
    diagnostics = _diagnostics(request)
    diagnostics.update(
        status="loading",
        last_operation="comparison",
        last_attempt=datetime.now(timezone.utc),
    )
    result = await load_january_comparison_inputs(
        request.app.state.elexon_client,
        decision_start,
        decision_end,
        settings.decision_cutoff_local_time,
        settings.forecast_publication_lookback_days,
    )
    days = [
        date.fromordinal(day)
        for day in range(decision_start.toordinal(), decision_end.toordinal() + 1)
    ]
    observations = select_point_in_time(
        days,
        result.forecasts,
        result.actuals,
        settings.decision_cutoff_local_time,
    )
    diagnostics.update(
        status="ok",
        last_operation="comparison",
        last_successful_refresh=datetime.now(timezone.utc),
        raw_forecast_records=result.raw_forecast_count,
        normalized_forecast_records=len(result.forecasts),
        invalid_forecast_records=result.invalid_forecasts,
        raw_actual_records=result.raw_actual_count,
        normalized_actual_records=len(result.actuals),
        invalid_actual_records=result.invalid_actuals,
        missing_forecast_records=sum(row.forecast_mw is None for row in observations),
        missing_actual_records=sum(row.actual_mw is None for row in observations),
        forecast_source_latest_time=max(
            (to_utc(row.publish_time) for row in result.forecasts), default=None
        ),
        actual_source_latest_time=max(
            (to_utc(row.start_time) for row in result.actuals), default=None
        ),
        message="Elexon data retrieved and normalized successfully.",
    )
    return observations


def _daily(observations: list[ComparisonObservation]) -> list[DailyAccuracy]:
    grouped: dict[date, list[ComparisonObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.decision_date, []).append(observation)
    return [
        DailyAccuracy(
            decision_date=day,
            delivery_date=rows[0].delivery_date,
            metrics=calculate_metrics(rows),
        )
        for day, rows in sorted(grouped.items())
    ]


def _selected(
    decision_start: date,
    decision_end: date,
    decision_date: date | None,
) -> tuple[date, date]:
    if decision_start < JANUARY_START or decision_end > JANUARY_END:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "date_out_of_scope",
                "message": "Decision dates must be within January 2026.",
            },
        )
    if decision_end < decision_start:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_date_range",
                "message": "decision_end must be on or after decision_start.",
            },
        )
    if decision_date is not None:
        if not decision_start <= decision_date <= decision_end:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "decision_date_out_of_range",
                    "message": "decision_date must be within the selected range.",
                },
            )
        return decision_date, decision_date
    return decision_start, decision_end


@router.get("/actuals", response_model=ActualDatasetResponse)
async def get_actuals(
    request: Request,
    start_date: date = Query(description="Inclusive FUELHH delivery date."),
    end_date: date = Query(description="Inclusive FUELHH delivery date."),
) -> ActualDatasetResponse:
    diagnostics = _diagnostics(request)
    diagnostics.update(
        status="loading",
        last_operation="actuals",
        last_attempt=datetime.now(timezone.utc),
    )
    try:
        raw = await request.app.state.elexon_client.fetch_actuals(start_date, end_date)
        records, invalid_count = _normalise(raw, normalize_actual)
    except ElexonAPIError as error:
        diagnostics.update(status="error", last_operation="actuals", message=str(error))
        raise HTTPException(status_code=502, detail={"code": "elexon_error", "message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_date_range", "message": str(error)}) from error
    diagnostics.update(
        status="ok", last_operation="actuals", last_attempt=datetime.now(timezone.utc),
        last_successful_refresh=datetime.now(timezone.utc),
        raw_actual_records=len(raw), normalized_actual_records=len(records),
        invalid_actual_records=invalid_count,
        actual_source_latest_time=max(
            (to_utc(row.start_time) for row in records), default=None
        ),
        message="FUELHH retrieval completed.",
    )
    return ActualDatasetResponse(dataset="FUELHH", record_count=len(records), records=records)


@router.get("/forecasts", response_model=ForecastDatasetResponse)
async def get_forecasts(
    request: Request,
    publish_from: datetime = Query(description="Inclusive timezone-aware forecast publication timestamp."),
    publish_to: datetime = Query(description="Inclusive timezone-aware forecast publication timestamp."),
) -> ForecastDatasetResponse:
    diagnostics = _diagnostics(request)
    diagnostics.update(
        status="loading",
        last_operation="forecasts",
        last_attempt=datetime.now(timezone.utc),
    )
    try:
        raw = await request.app.state.elexon_client.fetch_forecasts(publish_from, publish_to)
        records, invalid_count = _normalise(raw, normalize_forecast)
    except ElexonAPIError as error:
        diagnostics.update(status="error", last_operation="forecasts", message=str(error))
        raise HTTPException(status_code=502, detail={"code": "elexon_error", "message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_time_range", "message": str(error)}) from error
    diagnostics.update(
        status="ok", last_operation="forecasts", last_attempt=datetime.now(timezone.utc),
        last_successful_refresh=datetime.now(timezone.utc),
        raw_forecast_records=len(raw), normalized_forecast_records=len(records),
        invalid_forecast_records=invalid_count,
        forecast_source_latest_time=max(
            (to_utc(row.publish_time) for row in records), default=None
        ),
        message="WINDFOR retrieval completed.",
    )
    return ForecastDatasetResponse(dataset="WINDFOR", record_count=len(records), records=records)


@router.get("/forecast-revisions", response_model=ForecastRevisionResponse)
async def get_forecast_revisions(
    request: Request,
    decision_date: date = Query(description="January 2026 decision date."),
    target_time: datetime = Query(description="Timezone-aware delivery interval timestamp."),
) -> ForecastRevisionResponse:
    if not JANUARY_START <= decision_date <= JANUARY_END:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "date_out_of_scope",
                "message": "Decision dates must be within January 2026.",
            },
        )
    if target_time.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_target_time",
                "message": "target_time must include a timezone.",
            },
        )

    delivery_date = decision_date + timedelta(days=1)
    target_utc = to_utc(target_time)
    if target_utc not in expected_delivery_intervals(delivery_date):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_delivery_interval",
                "message": "target_time must be a 30-minute interval on the delivery date.",
            },
        )

    settings = get_settings()
    diagnostics = _diagnostics(request)
    diagnostics.update(
        status="loading",
        last_operation="forecast_revisions",
        last_attempt=datetime.now(timezone.utc),
    )
    publish_from = datetime.combine(
        decision_date - timedelta(days=settings.forecast_publication_lookback_days),
        time.min,
        tzinfo=ZoneInfo("Europe/London"),
    ).astimezone(timezone.utc)
    publish_to = datetime.now(timezone.utc)
    try:
        raw = await request.app.state.elexon_client.fetch_forecasts(
            publish_from, publish_to
        )
        forecasts, invalid_count = _normalise(raw, normalize_forecast)
    except ElexonAPIError as error:
        diagnostics.update(
            status="error", last_operation="forecast_revisions", message=str(error)
        )
        raise HTTPException(
            status_code=502,
            detail={"code": "elexon_error", "message": str(error)},
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_time_range", "message": str(error)},
        ) from error

    matching = [record for record in forecasts if to_utc(record.start_time) == target_utc]
    cutoff = decision_cutoff(decision_date, settings.decision_cutoff_local_time)
    selected, _ = select_latest_forecast(matching, cutoff)
    publications: dict[datetime, list[ForecastRecord]] = {}
    for record in matching:
        publications.setdefault(to_utc(record.publish_time), []).append(record)

    revisions = [
        ForecastRevision(
            publish_time=to_utc(record.publish_time),
            generation_mw=record.generation_mw,
            available_at_decision_time=to_utc(record.publish_time) <= cutoff,
            selected_for_decision=record is selected,
            duplicate_publication_timestamp=len(
                publications[to_utc(record.publish_time)]
            ) > 1,
            conflicting_duplicate=len(
                {
                    duplicate.generation_mw
                    for duplicate in publications[to_utc(record.publish_time)]
                }
            )
            > 1,
        )
        for record in sorted(
            matching,
            key=lambda item: (to_utc(item.publish_time), item.generation_mw),
        )
    ]

    diagnostics.update(
        status="ok",
        last_operation="forecast_revisions",
        last_attempt=datetime.now(timezone.utc),
        last_successful_refresh=datetime.now(timezone.utc),
        raw_forecast_records=len(raw),
        normalized_forecast_records=len(forecasts),
        invalid_forecast_records=invalid_count,
        forecast_source_latest_time=max(
            (to_utc(row.publish_time) for row in forecasts), default=None
        ),
        message="WINDFOR forecast revisions retrieved successfully.",
    )
    return ForecastRevisionResponse(
        decision_date=decision_date,
        delivery_date=delivery_date,
        target_time=target_utc,
        decision_cutoff=cutoff,
        decision_cutoff_local_time=settings.decision_cutoff_local_time,
        timezone="Europe/London",
        revisions=revisions,
    )


@router.get("/backtest", response_model=BacktestResponse)
async def get_backtest(
    request: Request,
    decision_start: date = Query(default=JANUARY_START),
    decision_end: date = Query(default=JANUARY_END),
    first_cutoff: time = Query(default=time(9), description="First Europe/London decision cutoff."),
    second_cutoff: time = Query(default=time(12), description="Second Europe/London decision cutoff."),
) -> BacktestResponse:
    start, end = _selected(decision_start, decision_end, None)
    if first_cutoff == second_cutoff:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "identical_cutoffs",
                "message": "Choose two different decision cutoffs to compare.",
            },
        )

    settings = get_settings()
    latest_cutoff = max(first_cutoff, second_cutoff)
    diagnostics = _diagnostics(request)
    diagnostics.update(
        status="loading",
        last_operation="backtest",
        last_attempt=datetime.now(timezone.utc),
    )
    try:
        result = await load_january_comparison_inputs(
            request.app.state.elexon_client,
            start,
            end,
            settings.decision_cutoff_local_time,
            settings.forecast_publication_lookback_days,
            latest_cutoff_local_time=latest_cutoff,
        )
    except ElexonAPIError as error:
        diagnostics.update(status="error", message=str(error))
        raise HTTPException(
            status_code=502,
            detail={"code": "elexon_error", "message": str(error)},
        ) from error
    except ValueError as error:
        diagnostics.update(status="error", message=str(error))
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_backtest_range", "message": str(error)},
        ) from error

    decision_dates = [
        date.fromordinal(day)
        for day in range(start.toordinal(), end.toordinal() + 1)
    ]
    response = run_backtest(
        decision_dates,
        result.forecasts,
        result.actuals,
        first_cutoff,
        second_cutoff,
    )
    selected_rows = response.first_cutoff_matched_observations
    diagnostics.update(
        status="ok",
        last_operation="backtest",
        last_attempt=datetime.now(timezone.utc),
        last_successful_refresh=datetime.now(timezone.utc),
        raw_forecast_records=result.raw_forecast_count,
        normalized_forecast_records=len(result.forecasts),
        invalid_forecast_records=result.invalid_forecasts,
        raw_actual_records=result.raw_actual_count,
        normalized_actual_records=len(result.actuals),
        invalid_actual_records=result.invalid_actuals,
        missing_forecast_records=response.first.forecast_metrics.missing_forecasts,
        missing_actual_records=response.first.forecast_metrics.missing_actuals,
        forecast_source_latest_time=max(
            (to_utc(row.publish_time) for row in result.forecasts), default=None
        ),
        actual_source_latest_time=max(
            (to_utc(row.start_time) for row in result.actuals), default=None
        ),
        message=f"Backtest completed with {selected_rows} matched first-cutoff intervals.",
    )
    return response


@router.get("/comparison", response_model=ComparisonResponse)
async def get_comparison(
    request: Request,
    decision_start: date = Query(default=JANUARY_START),
    decision_end: date = Query(default=JANUARY_END),
    decision_date: date | None = Query(default=None, description="Optionally restrict to one decision date."),
) -> ComparisonResponse:
    start, end = _selected(decision_start, decision_end, decision_date)
    observations, settings = await _load_observations(request, start, end)
    return ComparisonResponse(
        decision_cutoff_local_time=settings.decision_cutoff_local_time,
        timezone="Europe/London",
        decision_dates=sorted({row.decision_date for row in observations}),
        observation_count=len(observations),
        observations=observations,
    )


@router.get("/accuracy", response_model=AccuracyResponse)
async def get_accuracy(
    request: Request,
    decision_start: date = Query(default=JANUARY_START),
    decision_end: date = Query(default=JANUARY_END),
    decision_date: date | None = Query(default=None),
) -> AccuracyResponse:
    start, end = _selected(decision_start, decision_end, decision_date)
    observations, settings = await _load_observations(request, start, end)
    daily = _daily(observations)
    return AccuracyResponse(
        decision_cutoff_local_time=settings.decision_cutoff_local_time,
        timezone="Europe/London",
        decision_start=start,
        decision_end=end,
        by_decision_date=daily,
        by_delivery_date=sorted(daily, key=lambda row: row.delivery_date),
        overall=calculate_metrics(observations),
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    request: Request,
    decision_start: date = Query(default=JANUARY_START),
    decision_end: date = Query(default=JANUARY_END),
) -> HistoryResponse:
    start, end = _selected(decision_start, decision_end, None)
    observations, settings = await _load_observations(request, start, end)
    return HistoryResponse(
        decision_cutoff_local_time=settings.decision_cutoff_local_time,
        timezone="Europe/London",
        decision_start=start,
        decision_end=end,
        days=_daily(observations),
    )


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    request: Request,
    decision_start: date = Query(default=JANUARY_START),
    decision_end: date = Query(default=JANUARY_END),
) -> OverviewResponse:
    start, end = _selected(decision_start, decision_end, None)
    observations, settings = await _load_observations(request, start, end)
    return OverviewResponse(
        decision_cutoff_local_time=settings.decision_cutoff_local_time,
        timezone="Europe/London",
        decision_start=start,
        decision_end=end,
        generated_at=datetime.now(timezone.utc),
        metrics=calculate_metrics(observations),
        daily_history=_daily(observations),
    )


@router.get("/data-quality", response_model=DataDiagnosticsResponse)
async def get_data_quality(request: Request) -> DataDiagnosticsResponse:
    diagnostics = _diagnostics(request)
    client = request.app.state.elexon_client
    state = await request.app.state.ingestion_store.snapshot()
    runs = state["runs"][-10:]
    latest_run = runs[-1] if runs else {}
    settings = get_settings()
    return DataDiagnosticsResponse(
        **diagnostics,
        analytics_data_source="live_elexon",
        ingestion_enabled=settings.ingestion_enabled,
        stored_forecast_records=len(state["forecasts"]),
        stored_actual_records=len(state["actuals"]),
        stored_rejected_records=len(state["rejected"]),
        recent_ingestion_runs=runs,
        missing_actual_intervals=latest_run.get("missing_actual_intervals", 0),
        duplicate_forecast_records=latest_run.get("duplicate_forecast_records", 0),
        duplicate_actual_records=latest_run.get("duplicate_actual_records", 0),
        conflicting_forecast_groups=latest_run.get("conflicting_forecast_groups", 0),
        conflicting_actual_groups=latest_run.get("conflicting_actual_groups", 0),
        off_grid_forecast_records=latest_run.get("off_grid_forecast_records", 0),
        requests_made=client.requests_made,
        cache_hits=client.cache_hits,
        failed_requests=client.failed_requests,
    )


@router.post("/admin/ingestion/sync")
async def trigger_ingestion_sync(
    request: Request,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.ingestion_admin_token:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "admin_sync_disabled",
                "message": "Manual sync is disabled until an ingestion admin token is configured.",
            },
        )
    provided = request.headers.get("x-admin-token", "")
    if not hmac.compare_digest(
        provided.encode("utf-8"), settings.ingestion_admin_token.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_admin_token", "message": "A valid admin token is required."},
        )

    diagnostics = _diagnostics(request)
    diagnostics.update(
        status="loading",
        last_operation="manual_ingestion",
        last_attempt=datetime.now(timezone.utc),
        message="Manual Elexon ingestion is running.",
    )
    try:
        async with request.app.state.ingestion_lock:
            run = await run_incremental_ingestion(
                request.app.state.elexon_client,
                request.app.state.ingestion_store,
                settings.ingestion_lookback_days,
                settings.ingestion_forecast_overlap_hours,
            )
    except Exception as error:
        diagnostics.update(
            status="error",
            message=f"Manual Elexon ingestion failed: {error}",
        )
        logger.exception("Manual Elexon ingestion failed.")
        raise HTTPException(
            status_code=502,
            detail={"code": "ingestion_failed", "message": "Elexon ingestion failed; see pipeline diagnostics."},
        ) from error

    stored = await request.app.state.ingestion_store.snapshot()
    diagnostics.update(
        status="ok",
        last_operation="manual_ingestion",
        last_attempt=datetime.fromisoformat(run["started_at"]),
        last_successful_refresh=datetime.now(timezone.utc),
        raw_forecast_records=run["forecast_records_retrieved"],
        normalized_forecast_records=run["forecast_records_valid"],
        invalid_forecast_records=run["invalid_forecast_records"],
        raw_actual_records=run["actual_records_retrieved"],
        normalized_actual_records=run["actual_records_valid"],
        invalid_actual_records=run["invalid_actual_records"],
        forecast_source_latest_time=run["forecast_source_latest_time"],
        actual_source_latest_time=run["actual_source_latest_time"],
        missing_actual_records=run["missing_actual_intervals"],
        message="Manual Elexon ingestion completed.",
    )
    run["stored_forecast_records"] = len(stored["forecasts"])
    run["stored_actual_records"] = len(stored["actuals"])
    return run


@router.get("/performance", response_model=APIPerformanceResponse)
async def get_api_performance(request: Request) -> APIPerformanceResponse:
    metrics = request.app.state.api_metrics
    now = monotonic_time.monotonic()
    cutoff = now - 300
    samples = [sample for sample in metrics["samples"] if sample[0] >= cutoff]
    durations = sorted(sample[1] for sample in samples)
    server_errors = sum(sample[2] for sample in samples)
    total_requests = metrics["total_requests"]
    total_errors = metrics["total_server_errors"]
    return APIPerformanceResponse(
        uptime_seconds=now - metrics["started_at"],
        requests_in_window=len(samples),
        server_errors_in_window=server_errors,
        availability_pct=(
            (len(samples) - server_errors) / len(samples) * 100 if samples else None
        ),
        mean_response_time_ms=(
            sum(durations) / len(durations) if durations else None
        ),
        p95_response_time_ms=(
            durations[min(len(durations) - 1, ceil(len(durations) * 0.95) - 1)]
            if durations else None
        ),
        total_requests=total_requests,
        total_server_errors=total_errors,
    )
