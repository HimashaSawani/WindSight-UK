from functools import lru_cache
from datetime import time

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "WindSight UK API"
    frontend_origins: str = "http://localhost:5173,http://localhost:8080"
    elexon_api_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = Field(default=30, gt=0, le=300)
    elexon_max_retries: int = Field(default=3, ge=0, le=10)
    cache_dir: str = ".cache/elexon"
    cache_ttl_seconds: int = Field(default=900, ge=0)
    cache_refresh: bool = False
    decision_cutoff_local_time: time = time(hour=12)
    forecast_publication_lookback_days: int = Field(default=31, ge=1, le=90)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WINDSIGHT_",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
