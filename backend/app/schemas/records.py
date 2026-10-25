from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NormalizedRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    start_time: datetime = Field(serialization_alias="startTime")
    generation_mw: float = Field(serialization_alias="generation")
    source_metadata: dict[str, Any]


class ForecastRecord(NormalizedRecord):
    publish_time: datetime = Field(serialization_alias="publishTime")


class ActualRecord(NormalizedRecord):
    fuel_type: Literal["WIND"] = Field(serialization_alias="fuelType")


class ComparisonObservation(BaseModel):
    decision_date: date
    delivery_date: date
    decision_cutoff: datetime
    target_time: datetime
    forecast_publish_time: datetime | None
    forecast_mw: float | None
    actual_mw: float | None
    forecast_age_minutes: float | None
    availability: Literal["matched", "missing_forecast", "missing_actual", "missing_both"]
    error_mw: float | None = None
    conflicting_forecast_duplicate: bool = False
    conflicting_actual_duplicate: bool = False
    forecast_source_metadata: dict[str, Any] | None = None
    actual_source_metadata: dict[str, Any] | None = None
