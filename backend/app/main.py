import asyncio
import time
import logging
from contextlib import asynccontextmanager
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.clients.elexon import DiskCache, ElexonClient
from app.services.automated_ingestion import run_incremental_ingestion
from app.services.ingestion_store import IngestionStore, acquire_ingestion_lease

settings = get_settings()
logger = logging.getLogger(__name__)


async def _ingestion_loop(application: FastAPI) -> None:
    while True:
        try:
            application.state.data_diagnostics.update(
                status="loading",
                last_operation="scheduled_ingestion",
                last_attempt=datetime.now(timezone.utc),
                message="Scheduled Elexon ingestion is running.",
            )
            async with application.state.ingestion_lock:
                run = await run_incremental_ingestion(
                    application.state.elexon_client,
                    application.state.ingestion_store,
                    settings.ingestion_lookback_days,
                    settings.ingestion_forecast_overlap_hours,
                )
            diagnostics = application.state.data_diagnostics
            diagnostics.update(
                status="ok",
                last_operation="scheduled_ingestion",
                last_attempt=datetime.fromisoformat(run["started_at"]),
                last_successful_refresh=datetime.now(timezone.utc),
                raw_forecast_records=run["forecast_records_retrieved"],
                normalized_forecast_records=run["forecast_records_valid"],
                invalid_forecast_records=run["invalid_forecast_records"],
                raw_actual_records=run["actual_records_retrieved"],
                normalized_actual_records=run["actual_records_valid"],
                invalid_actual_records=run["invalid_actual_records"],
                missing_actual_records=run["missing_actual_intervals"],
                forecast_source_latest_time=run["forecast_source_latest_time"],
                actual_source_latest_time=run["actual_source_latest_time"],
                message="Scheduled Elexon ingestion completed.",
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            application.state.data_diagnostics.update(
                status="error",
                last_operation="scheduled_ingestion",
                last_attempt=datetime.now(timezone.utc),
                message=f"Scheduled ingestion failed: {error}",
            )
            logger.exception("Scheduled Elexon ingestion failed.")
        await asyncio.sleep(settings.ingestion_interval_seconds)


@asynccontextmanager
async def lifespan(application: FastAPI):
    ingestion_lease = None
    if settings.ingestion_enabled:
        ingestion_lease = acquire_ingestion_lease(settings.ingestion_store_path)

    application.state.api_metrics = {
        "started_at": time.monotonic(),
        "samples": deque(maxlen=10000),
        "total_requests": 0,
        "total_server_errors": 0,
    }
    application.state.elexon_client = ElexonClient(
        base_url=settings.elexon_api_base_url,
        timeout_seconds=settings.elexon_timeout_seconds,
        max_retries=settings.elexon_max_retries,
        cache=DiskCache(
            settings.cache_dir,
            settings.cache_ttl_seconds,
            refresh=settings.cache_refresh,
        ),
    )
    application.state.analysis_lock = asyncio.Lock()
    application.state.analysis_cache = {}
    application.state.analysis_inflight = {}
    application.state.ingestion_store = IngestionStore(settings.ingestion_store_path)
    application.state.ingestion_lock = asyncio.Lock()
    application.state.data_diagnostics = {
        "status": "scheduled" if settings.ingestion_enabled else "not_requested",
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
        "message": (
            "Automated ingestion is enabled."
            if settings.ingestion_enabled
            else "No Elexon data has been requested in this process."
        ),
    }
    application.state.ingestion_task = (
        asyncio.create_task(_ingestion_loop(application))
        if settings.ingestion_enabled
        else None
    )
    try:
        yield
    finally:
        if application.state.ingestion_task is not None:
            application.state.ingestion_task.cancel()
            try:
                await application.state.ingestion_task
            except asyncio.CancelledError:
                pass
        await application.state.elexon_client.close()
        if ingestion_lease is not None:
            ingestion_lease.release()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.middleware("http")
async def record_api_performance(request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    started = time.monotonic()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        metrics = request.app.state.api_metrics
        failed = status_code >= 500
        duration_ms = (time.monotonic() - started) * 1000
        metrics["samples"].append((time.monotonic(), duration_ms, failed))
        metrics["total_requests"] += 1
        metrics["total_server_errors"] += int(failed)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(api_router)
