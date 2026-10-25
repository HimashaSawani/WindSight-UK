from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import data
from app.main import app
from app.schemas.records import ActualRecord, ForecastRecord


def test_analysis_endpoints_return_typed_metrics_and_filter_validation(monkeypatch) -> None:
    async def fake_load(*args, **kwargs):
        return SimpleNamespace(
            forecasts=[
                ForecastRecord(
                    start_time=datetime(2026, 1, 2, 0, tzinfo=timezone.utc),
                    publish_time=datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
                    generation_mw=120,
                    source_metadata={"test_data": True},
                )
            ],
            actuals=[
                ActualRecord(
                    start_time=datetime(2026, 1, 2, 0, tzinfo=timezone.utc),
                    generation_mw=100,
                    fuel_type="WIND",
                    source_metadata={"test_data": True},
                )
            ],
            raw_forecast_count=1,
            raw_actual_count=1,
            invalid_forecasts=0,
            invalid_actuals=0,
        )

    monkeypatch.setattr(data, "load_january_comparison_inputs", fake_load)
    with TestClient(app) as client:
        accuracy = client.get(
            "/api/accuracy",
            params={"decision_start": "2026-01-01", "decision_end": "2026-01-01"},
        )
        overview = client.get(
            "/api/overview",
            params={"decision_start": "2026-01-01", "decision_end": "2026-01-01"},
        )
        comparison = client.get(
            "/api/comparison",
            params={"decision_date": "2026-01-01"},
        )
        history = client.get(
            "/api/history",
            params={"decision_start": "2026-01-01", "decision_end": "2026-01-01"},
        )
        quality = client.get("/api/data-quality")
        invalid = client.get(
            "/api/history",
            params={"decision_start": "2026-01-02", "decision_end": "2026-01-01"},
        )

    assert accuracy.status_code == 200
    assert accuracy.json()["overall"]["mae_mw"] == 20
    assert accuracy.json()["overall"]["mean_bias_error_mw"] == 20
    assert accuracy.json()["overall"]["matched_observations"] == 1
    assert overview.status_code == 200
    assert overview.json()["decision_start"] == "2026-01-01"
    assert comparison.status_code == 200
    assert comparison.json()["observations"][0]["error_mw"] == 20
    assert history.status_code == 200
    assert history.json()["days"][0]["metrics"]["matched_observations"] == 1
    assert quality.status_code == 200
    assert quality.json()["last_successful_refresh"] is not None
    assert invalid.status_code == 422


def test_backtest_compares_common_intervals_and_reports_persistence_baseline(
    monkeypatch,
) -> None:
    async def fake_load(*args, **kwargs):
        assert kwargs["latest_cutoff_local_time"].hour == 12
        return SimpleNamespace(
            forecasts=[
                ForecastRecord(
                    start_time=datetime(2026, 1, 2, 0, tzinfo=timezone.utc),
                    publish_time=datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
                    generation_mw=80,
                    source_metadata={},
                ),
                ForecastRecord(
                    start_time=datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc),
                    publish_time=datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
                    generation_mw=100,
                    source_metadata={},
                ),
                ForecastRecord(
                    start_time=datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc),
                    publish_time=datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
                    generation_mw=120,
                    source_metadata={},
                ),
            ],
            actuals=[
                ActualRecord(
                    start_time=datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc),
                    generation_mw=110,
                    fuel_type="WIND",
                    source_metadata={},
                )
            ],
            raw_forecast_count=3,
            raw_actual_count=1,
            invalid_forecasts=0,
            invalid_actuals=0,
        )

    monkeypatch.setattr(data, "load_january_comparison_inputs", fake_load)
    with TestClient(app) as client:
        response = client.get(
            "/api/backtest",
            params={
                "decision_start": "2026-01-01",
                "decision_end": "2026-01-01",
                "first_cutoff": "09:00",
                "second_cutoff": "12:00",
            },
        )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["first"]["forecast_metrics"]["mae_mw"] == 10
    assert result["second"]["forecast_metrics"]["mae_mw"] == 10
    assert result["common"]["matched_observations"] == 1
    assert result["common"]["first_cutoff_metrics"]["matched_observations"] == 1
    assert result["first"]["persistence_metrics"]["mae_mw"] == 30
    assert result["first_cutoff_error_quantiles_mw"] == {
        "p10": -10,
        "p50": -10,
        "p90": -10,
    }


def test_backtest_rejects_identical_cutoffs() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/backtest",
            params={"first_cutoff": "09:00", "second_cutoff": "09:00"},
        )
        performance = client.get("/api/performance")

    assert response.status_code == 422
    assert performance.status_code == 200
    assert performance.json()["requests_in_window"] >= 1
