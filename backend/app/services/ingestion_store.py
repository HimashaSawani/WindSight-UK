import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _canonical(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)


def _record_identity(dataset: str, record: dict[str, Any]) -> str:
    identity = _canonical(record)
    return hashlib.sha256(f"{dataset}:{identity}".encode("utf-8")).hexdigest()


class IngestionStore:
    """Small single-process append-by-rewrite store for source records and run history."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._lock = asyncio.Lock()

    def _read(self) -> dict[str, Any]:
        try:
            contents = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {
                "version": 1,
                "forecasts": [],
                "actuals": [],
                "rejected": [],
                "runs": [],
                "checkpoints": {},
            }
        try:
            state = json.loads(contents)
            if (
                not isinstance(state, dict)
                or state.get("version") != 1
                or not all(isinstance(state.get(key), list) for key in (
                    "forecasts", "actuals", "rejected", "runs"
                ))
                or not isinstance(state.get("checkpoints"), dict)
            ):
                raise ValueError("Ingestion store has an invalid schema.")
            return state
        except (json.JSONDecodeError, ValueError) as error:
            logger.error("Unable to read ingestion store %s: %s", self.path, error)
            raise RuntimeError("Persisted ingestion store is invalid; refusing to overwrite it.") from error

    async def _write(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state, separators=(",", ":"), default=str)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        await asyncio.to_thread(self.path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(temporary.write_text, payload, encoding="utf-8")
        await asyncio.to_thread(temporary.replace, self.path)

    async def merge_records(
        self,
        forecasts: list[dict[str, Any]],
        actuals: list[dict[str, Any]],
        rejected: list[dict[str, Any]],
    ) -> dict[str, int]:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            counters: dict[str, int] = {}
            for dataset, incoming in (
                ("forecasts", forecasts),
                ("actuals", actuals),
                ("rejected", rejected),
            ):
                existing = state[dataset]
                seen = {_record_identity(dataset, record) for record in existing}
                added = 0
                duplicates = 0
                for record in incoming:
                    identity = _record_identity(dataset, record)
                    if identity in seen:
                        duplicates += 1
                        continue
                    seen.add(identity)
                    existing.append(record)
                    added += 1
                counters[f"{dataset}_added"] = added
                counters[f"{dataset}_duplicates"] = duplicates
            await self._write(state)
            return counters

    async def save_run(self, run: dict[str, Any], checkpoint: datetime | None = None) -> None:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            state["runs"].append(run)
            state["runs"] = state["runs"][-100:]
            if checkpoint is not None:
                current = state["checkpoints"].get("forecast_publish_to")
                if current is None or checkpoint.isoformat() > current:
                    state["checkpoints"]["forecast_publish_to"] = checkpoint.isoformat()
            await self._write(state)

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return await asyncio.to_thread(self._read)

    async def forecast_checkpoint(self) -> datetime | None:
        state = await self.snapshot()
        value = state["checkpoints"].get("forecast_publish_to")
        return datetime.fromisoformat(value) if value else None

    async def record_failed_run(self, run: dict[str, Any]) -> None:
        failed = dict(run)
        failed.update(status="failed", finished_at=datetime.now(timezone.utc).isoformat())
        await self.save_run(failed)
