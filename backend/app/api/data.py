import logging
import asyncio
import time as monotonic_time
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.clients.elexon import ElexonAPIError
from app.core.config import get_settings
from app.schemas.analysis import (
    AccuracyResponse,
    DailyAccuracy,
    ForecastRevision,
    ForecastRevisionResponse,
    HistoryResponse,
    OverviewResponse,
    ComparisonResponse,
)
from app.schemas.records import ActualRecord, ComparisonObservation, ForecastRecord
from app.services.ingestion import load_january_comparison_inputs
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
    status: str
    last_operation: str | None
    last_successful_refresh: datetime | None
    raw_forecast_records: int
    normalized_forecast_records: int
    invalid_forecast_records: int
    raw_actual_records: int
    normalized_actual_records: int
    invalid_actual_records: int
    requests_made: int
    cache_hits: int
    message: str


def _diagnostics(request: Request) -> dict[str, Any]:
    if not hasattr(request.app.state, "data_diagnostics"):
        request.app.state.data_diagnostics = {
            "status": "not_requested",
            "last_operation": None,
            "last_successful_refresh": None,
            "raw_forecast_records": 0,
            "normalized_forecast_records": 0,
            "invalid_forecast_records": 0,
            "raw_actual_records": 0,
            "normalized_actual_records": 0,
            "invalid_actual_records": 0,
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
    result = await load_january_comparison_inputs(
        request.app.state.elexon_client,
        decision_start,
        decision_end,
        settings.decision_cutoff_local_time,
        settings.forecast_publication_lookback_days,
    )
    diagnostics = _diagnostics(request)
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
        message="Elexon data retrieved and normalized successfully.",
    )
    days = [
        date.fromordinal(day)
        for day in range(decision_start.toordinal(), decision_end.toordinal() + 1)
    ]
    return select_point_in_time(
        days,
        result.forecasts,
        result.actuals,
        settings.decision_cutoff_local_time,
    )


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
    try:
        raw = await request.app.state.elexon_client.fetch_actuals(start_date, end_date)
        records, invalid_count = _normalise(raw, normalize_actual)
    except ElexonAPIError as error:
        diagnostics.update(status="error", last_operation="actuals", message=str(error))
        raise HTTPException(status_code=502, detail={"code": "elexon_error", "message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_date_range", "message": str(error)}) from error
    diagnostics.update(
        status="ok", last_operation="actuals", last_successful_refresh=datetime.now(timezone.utc),
        raw_actual_records=len(raw), normalized_actual_records=len(records),
        invalid_actual_records=invalid_count, message="FUELHH retrieval completed.",
    )
    return ActualDatasetResponse(dataset="FUELHH", record_count=len(records), records=records)


@router.get("/forecasts", response_model=ForecastDatasetResponse)
async def get_forecasts(
    request: Request,
    publish_from: datetime = Query(description="Inclusive timezone-aware forecast publication timestamp."),
    publish_to: datetime = Query(description="Inclusive timezone-aware forecast publication timestamp."),
) -> ForecastDatasetResponse:
    diagnostics = _diagnostics(request)
    try:
        raw = await request.app.state.elexon_client.fetch_forecasts(publish_from, publish_to)
        records, invalid_count = _normalise(raw, normalize_forecast)
    except ElexonAPIError as error:
        diagnostics.update(status="error", last_operation="forecasts", message=str(error))
        raise HTTPException(status_code=502, detail={"code": "elexon_error", "message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_time_range", "message": str(error)}) from error
    diagnostics.update(
        status="ok", last_operation="forecasts", last_successful_refresh=datetime.now(timezone.utc),
        raw_forecast_records=len(raw), normalized_forecast_records=len(records),
        invalid_forecast_records=invalid_count, message="WINDFOR retrieval completed.",
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
    publish_from = datetime.combine(
        decision_date - timedelta(days=settings.forecast_publication_lookback_days),
        time.min,
        tzinfo=ZoneInfo("Europe/London"),
    ).astimezone(timezone.utc)
    publish_to = datetime.now(timezone.utc)
    diagnostics = _diagnostics(request)
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
        for record in sorted(matching, key=lambda item: to_utc(item.publish_time))
    ]

    diagnostics.update(
        status="ok",
        last_operation="forecast_revisions",
        last_successful_refresh=datetime.now(timezone.utc),
        raw_forecast_records=len(raw),
        normalized_forecast_records=len(forecasts),
        invalid_forecast_records=invalid_count,
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
    return DataDiagnosticsResponse(
        **diagnostics,
        requests_made=client.requests_made,
        cache_hits=client.cache_hits,
    )
