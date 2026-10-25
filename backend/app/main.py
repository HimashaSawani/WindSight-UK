import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.clients.elexon import DiskCache, ElexonClient

settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(api_router)
