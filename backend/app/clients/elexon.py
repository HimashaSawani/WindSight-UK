import asyncio
import hashlib
import json
import logging
import random
import time
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


class ElexonAPIError(RuntimeError):
    pass


class DiskCache:
    def __init__(self, directory: str, ttl_seconds: int, refresh: bool = False) -> None:
        self.directory = Path(directory)
        self.ttl_seconds = ttl_seconds
        self.refresh = refresh
        self._lock = asyncio.Lock()

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"

    async def get(self, key: str) -> list[dict[str, Any]] | None:
        if self.refresh or self.ttl_seconds == 0:
            return None
        path = self._path(key)
        try:
            payload = await asyncio.to_thread(path.read_text, encoding="utf-8")
            entry = json.loads(payload)
            records = entry["records"]
            if not isinstance(records, list) or not all(
                isinstance(record, dict) for record in records
            ):
                raise ValueError("Cache entry has an invalid records array.")
            if time.time() - entry["created_at"] > self.ttl_seconds:
                return None
            return records
        except FileNotFoundError:
            return None
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            logger.warning("Ignoring unreadable Elexon cache entry %s: %s", path.name, error)
            return None

    async def put(self, key: str, records: list[dict[str, Any]]) -> None:
        if self.ttl_seconds == 0:
            return
        path = self._path(key)
        payload = json.dumps(
            {"created_at": time.time(), "records": records},
            separators=(",", ":"),
        )
        async with self._lock:
            await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            await asyncio.to_thread(temporary.write_text, payload, encoding="utf-8")
            await asyncio.to_thread(temporary.replace, path)


class ElexonClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        cache: DiskCache,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.max_retries = max_retries
        self.cache = cache
        self._owns_client = client is None
        self.http = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._semaphore = asyncio.Semaphore(4)
        self.requests_made = 0
        self.cache_hits = 0

    async def close(self) -> None:
        if self._owns_client:
            await self.http.aclose()

    async def _get(self, resource: str, params: dict[str, str]) -> list[dict[str, Any]]:
        async with self._semaphore:
            return await self._request(resource, params)

    async def _request(self, resource: str, params: dict[str, str]) -> list[dict[str, Any]]:
        url = urljoin(self.base_url, f"datasets/{resource}/stream")
        key = json.dumps({"url": url, "params": params}, sort_keys=True)
        cached = await self.cache.get(key)
        if cached is not None:
            self.cache_hits += 1
            return cached

        for attempt in range(self.max_retries + 1):
            self.requests_made += 1
            try:
                response = await self.http.get(url, params=params)
            except httpx.TimeoutException as error:
                if attempt == self.max_retries:
                    raise ElexonAPIError(f"Elexon request timed out: {url}") from error
                await asyncio.sleep(self._backoff(attempt))
                continue
            except httpx.RequestError as error:
                if attempt == self.max_retries:
                    raise ElexonAPIError(f"Elexon request failed: {error}") from error
                await asyncio.sleep(self._backoff(attempt))
                continue

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == self.max_retries:
                    raise ElexonAPIError(
                        f"Elexon returned HTTP {response.status_code} after retries."
                    )
                retry_after = response.headers.get("Retry-After")
                delay = self._retry_after(retry_after)
                await asyncio.sleep(delay if delay is not None else self._backoff(attempt))
                continue
            if response.is_error:
                raise ElexonAPIError(
                    f"Elexon returned HTTP {response.status_code}: {response.text[:500]}"
                )
            try:
                decoded = response.json()
            except json.JSONDecodeError as error:
                raise ElexonAPIError("Elexon response was not valid JSON.") from error
            if isinstance(decoded, dict) and isinstance(decoded.get("data"), list):
                decoded = decoded["data"]
            if not isinstance(decoded, list) or not all(
                isinstance(record, dict) for record in decoded
            ):
                raise ElexonAPIError("Elexon response did not contain a record array.")
            await self.cache.put(key, decoded)
            return decoded
        raise ElexonAPIError("Elexon request retry loop ended unexpectedly.")

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(30.0, 0.5 * (2**attempt)) + random.random() * 0.25

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return min(60.0, max(0.0, float(value)))
        except ValueError:
            try:
                retry_at = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
                return min(
                    60.0,
                    max(0.0, (retry_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds()),
                )
            except ValueError:
                return None

    async def fetch_actuals(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date.")
        requests = []
        current = start_date
        while current <= end_date:
            requests.append(
                (current, self._get(
                    "FUELHH",
                    {
                        "settlementDateFrom": current.isoformat(),
                        "settlementDateTo": current.isoformat(),
                        "fuelType": "WIND",
                    },
                ))
            )
            current += timedelta(days=1)
        records = []
        for delivery_day, day_records in zip(
            [item[0] for item in requests],
            await asyncio.gather(*(item[1] for item in requests)),
        ):
            records.extend(
                record
                for record in day_records
                if record.get("fuelType") == "WIND"
                and record.get("settlementDate", delivery_day.isoformat())
                == delivery_day.isoformat()
            )
        return records

    async def fetch_forecasts(
        self,
        publish_from: datetime,
        publish_to: datetime,
    ) -> list[dict[str, Any]]:
        if publish_from.tzinfo is None or publish_to.tzinfo is None:
            raise ValueError("Forecast publication window timestamps must be timezone-aware.")
        start_utc = publish_from.astimezone(timezone.utc)
        end_utc = publish_to.astimezone(timezone.utc)
        if end_utc < start_utc:
            raise ValueError("publish_to must not be before publish_from.")
        chunks: list[tuple[datetime, datetime, bool, Any]] = []
        current_day = start_utc.date()
        final_day = end_utc.date()
        while current_day <= final_day:
            day_from = max(
                start_utc,
                datetime.combine(current_day, datetime_time.min, tzinfo=timezone.utc),
            )
            day_to = min(
                end_utc,
                datetime.combine(
                    current_day + timedelta(days=1),
                    datetime_time.min,
                    tzinfo=timezone.utc,
                ),
            )
            chunks.append(
                (
                    day_from,
                    day_to,
                    current_day == final_day,
                    self._get(
                        "WINDFOR",
                        {
                            "publishDateTimeFrom": day_from.isoformat().replace("+00:00", "Z"),
                            "publishDateTimeTo": day_to.isoformat().replace("+00:00", "Z"),
                        },
                    ),
                )
            )
            current_day += timedelta(days=1)
        responses = await asyncio.gather(*(chunk[3] for chunk in chunks))
        records: list[dict[str, Any]] = []
        for (lower, upper, final_inclusive, _), response_records in zip(chunks, responses):
            for record in response_records:
                publish_time = record.get("publishTime")
                if not isinstance(publish_time, str):
                    records.append(record)
                    continue
                try:
                    published = datetime.fromisoformat(
                        publish_time.replace("Z", "+00:00")
                    ).astimezone(timezone.utc)
                except ValueError:
                    records.append(record)
                    continue
                if lower <= published and (
                    published < upper or (final_inclusive and published == upper)
                ):
                    records.append(record)
        return records
