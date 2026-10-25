from fastapi import APIRouter

from app.api.data import router as data_router
from app.api.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(data_router, tags=["data"])
