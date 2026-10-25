import json
from datetime import date, datetime, timezone

import httpx
import pytest

from app.clients.elexon import DiskCache, ElexonAPIError, ElexonClient


@pytest.mark.asyncio
async def test_fetches_actual_wind_by_inclusive_delivery_date(tmp_path) -> None:
    requested = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return httpx.Response(200, json=[
            {"fuelType": "WIND", "generation": 0},
            {"fuelType": "CCGT", "generation": 10},
        ])

    client = ElexonClient(
        "https://example.test/api/v1",
        2,
        0,
        DiskCache(str(tmp_path), 60),
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    records = await client.fetch_actuals(date(2026, 1, 2), date(2026, 1, 2))

    assert len(records) == 1
    assert records[0]["fuelType"] == "WIND"
    assert requested[0].url.path.endswith("/datasets/FUELHH/stream")
    assert requested[0].url.params["settlementDateFrom"] == "2026-01-02"
    assert requested[0].url.params["fuelType"] == "WIND"
    await client.http.aclose()


@pytest.mark.asyncio
async def test_fetches_forecasts_with_publication_time_range_and_keeps_revisions(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[
            {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T10:00:00Z", "generation": 10},
            {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T11:00:00Z", "generation": 20},
        ])

    transport_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElexonClient("https://example.test/api/v1", 2, 0, DiskCache(str(tmp_path), 60), transport_client)
    records = await client.fetch_forecasts(
        datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 23, tzinfo=timezone.utc),
    )

    assert len(records) == 2
    assert records[0]["publishTime"] != records[1]["publishTime"]
    await transport_client.aclose()


@pytest.mark.asyncio
async def test_forecast_time_chunks_do_not_duplicate_boundary_publications(tmp_path) -> None:
    response_records = [
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T23:30:00Z", "generation": 1},
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-02T00:00:00Z", "generation": 2},
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_records)

    transport_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElexonClient("https://example.test/api/v1", 2, 0, DiskCache(str(tmp_path), 60), transport_client)
    records = await client.fetch_forecasts(
        datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 2, 0, tzinfo=timezone.utc),
    )

    assert len(records) == 2
    assert client.requests_made == 2
    await transport_client.aclose()


@pytest.mark.asyncio
async def test_http_error_is_reported_without_success_shaped_fallback(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    transport_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElexonClient("https://example.test/api/v1", 2, 0, DiskCache(str(tmp_path), 60), transport_client)

    with pytest.raises(ElexonAPIError, match="HTTP 503"):
        await client.fetch_actuals(date(2026, 1, 2), date(2026, 1, 2))
    await transport_client.aclose()


@pytest.mark.asyncio
async def test_retries_rate_limit_using_retry_after(tmp_path) -> None:
    request_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=[])

    transport_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElexonClient("https://example.test/api/v1", 2, 1, DiskCache(str(tmp_path), 60), transport_client)
    records = await client.fetch_actuals(date(2026, 1, 2), date(2026, 1, 2))

    assert records == []
    assert request_count == 2
    await transport_client.aclose()


@pytest.mark.asyncio
async def test_disk_cache_avoids_repeated_request(tmp_path) -> None:
    request_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, content=json.dumps([{"fuelType": "WIND"}]))

    transport_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElexonClient("https://example.test/api/v1", 2, 0, DiskCache(str(tmp_path), 60), transport_client)
    await client.fetch_actuals(date(2026, 1, 2), date(2026, 1, 2))
    await client.fetch_actuals(date(2026, 1, 2), date(2026, 1, 2))

    assert request_count == 1
    assert client.cache_hits == 1
    await transport_client.aclose()
