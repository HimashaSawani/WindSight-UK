from datetime import datetime, timezone

import pytest

from app.services.normalization import normalize_actual, normalize_forecast


def test_normalizes_timestamp_offsets_to_utc_and_preserves_source_metadata() -> None:
    record = normalize_forecast({
        "dataset": "WINDFOR",
        "startTime": "2026-01-02T01:00:00+01:00",
        "publishTime": "2026-01-01T11:00:00Z",
        "generation": 0,
    })

    assert record.start_time == datetime(2026, 1, 2, 0, tzinfo=timezone.utc)
    assert record.generation_mw == 0
    assert record.source_metadata["dataset"] == "WINDFOR"
    assert record.model_dump(by_alias=True)["startTime"] == datetime(
        2026, 1, 2, 0, tzinfo=timezone.utc
    )
    assert record.model_dump(by_alias=True)["publishTime"] == datetime(
        2026, 1, 1, 11, tzinfo=timezone.utc
    )


def test_rejects_timezone_naive_source_timestamps() -> None:
    with pytest.raises(ValueError, match="include a timezone"):
        normalize_forecast({
            "startTime": "2026-01-02T00:00:00",
            "publishTime": "2026-01-01T11:00:00Z",
            "generation": 100,
        })


def test_rejects_missing_or_non_numeric_generation() -> None:
    with pytest.raises(ValueError, match="missing or not numeric"):
        normalize_actual({
            "startTime": "2026-01-02T00:00:00Z",
            "fuelType": "WIND",
            "generation": None,
        })


def test_actuals_exclude_non_wind_fuels() -> None:
    with pytest.raises(ValueError, match="not fuelType WIND"):
        normalize_actual({
            "startTime": "2026-01-02T00:00:00Z",
            "fuelType": "CCGT",
            "generation": 1,
        })
