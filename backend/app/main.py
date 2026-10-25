import asyncio
import time
from contextlib import asynccontextmanager
from collections import deque

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.clients.elexon import DiskCache, ElexonClient

settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.api_metrics = {
        "started_at": time.monotonic(),
        "samples": deque(maxlen=1000),
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
    yield
    await application.state.elexon_client.close()


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
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(api_router)
