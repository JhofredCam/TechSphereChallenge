"""JSONL event logging and deterministic call/turn metric aggregation."""

from __future__ import annotations

import json
import math
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_MODEL_VERSION = "llama-3.1-8b-instant"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _json_safe(value: Any) -> Any:
    """Convert common service values into JSON primitives."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_safe(to_dict())
    if hasattr(value, "value") and isinstance(value.value, (str, int, float, bool)):
        return value.value
    return str(value)


def percentile(values: Iterable[float], percentage: float) -> float | None:
    """Return a linearly interpolated percentile, or ``None`` for no samples."""

    numbers = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not numbers:
        return None
    if percentage <= 0:
        return numbers[0]
    if percentage >= 100:
        return numbers[-1]
    position = (len(numbers) - 1) * (percentage / 100.0)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return numbers[lower]
    fraction = position - lower
    return numbers[lower] + (numbers[upper] - numbers[lower]) * fraction


def _timestamp_difference_ms(start: Any, end: Any) -> float | None:
    if start is None or end is None:
        return None
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        left = float(start)
        right = float(end)
        difference = right - left
        if difference < 0:
            return None
        # Browser code sends ISO timestamps. For numeric integrations, distinguish
        # epoch milliseconds from epoch/monotonic seconds by the magnitude of the
        # clock values rather than the magnitude of the measured interval.
        return difference if max(abs(left), abs(right)) >= 100_000_000_000 else difference * 1000
    try:
        left = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        right = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        if left.tzinfo is None:
            left = left.replace(tzinfo=timezone.utc)
        if right.tzinfo is None:
            right = right.replace(tzinfo=timezone.utc)
        difference = (right - left).total_seconds() * 1000.0
        return difference if difference >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


class MetricsService:
    """Append immutable turn events and compute metrics from those events.

    The file is optional for in-memory tests.  With a file-backed ``Database``
    the default location is next to the SQLite database, keeping runtime state
    in the configured data directory without requiring another setting.
    """

    def __init__(
        self,
        database: Any | None = None,
        log_path: str | Path | None = None,
        *,
        clock: Any | None = None,
    ) -> None:
        self.database = database
        self._clock = clock or _utc_now
        self._lock = threading.RLock()
        self._memory_events: list[dict[str, Any]] = []

        if log_path is not None:
            self.log_path: Path | None = Path(log_path)
        else:
            database_path = getattr(database, "path", None)
            if database_path is not None and str(database_path) != ":memory:":
                self.log_path = Path(database_path).parent / "events.jsonl"
            else:
                self.log_path = None
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        event: Mapping[str, Any] | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        """Write one JSONL event and return the exact serialized payload."""

        payload: dict[str, Any] = dict(event or {})
        payload.update(fields)
        record: dict[str, Any] = {
            "event_type": str(event_type),
            "created_at": str(payload.pop("created_at", self._clock())),
        }
        record.update(_json_safe(payload))
        with self._lock:
            self._memory_events.append(record)
            if self.log_path is not None:
                line = json.dumps(record, ensure_ascii=False, sort_keys=True)
                with self.log_path.open("a", encoding="utf-8") as stream:
                    stream.write(line)
                    stream.write("\n")
        return record

    record_event = log_event
    write_event = log_event

    def record_turn(
        self,
        event: Mapping[str, Any] | None = None,
        *,
        call_id: str | None = None,
        turn_id: str | None = None,
        speech_ended_at: Any | None = None,
        audio_started_at: Any | None = None,
        latency_ms: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        model_calls: int | None = None,
        rag_queries: int | None = None,
        source_ids: Iterable[Any] | None = None,
        model_version: str | None = None,
        created_at: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Record the metrics contract for one conversational turn."""

        payload: dict[str, Any] = dict(event or {})
        explicit = {
            "call_id": call_id,
            "turn_id": turn_id,
            "speech_ended_at": speech_ended_at,
            "audio_started_at": audio_started_at,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model_calls": model_calls,
            "rag_queries": rag_queries,
            "source_ids": list(source_ids) if source_ids is not None else None,
            "model_version": model_version,
            "created_at": created_at,
        }
        for key, value in explicit.items():
            if value is not None:
                payload[key] = value
        payload.update(extra)

        if payload.get("latency_ms") is None:
            derived_latency = _timestamp_difference_ms(
                payload.get("speech_ended_at"),
                payload.get("audio_started_at"),
            )
            if derived_latency is not None:
                payload["latency_ms"] = derived_latency

        payload.setdefault("input_tokens", 0)
        payload.setdefault("output_tokens", 0)
        payload.setdefault("model_calls", 0)
        payload.setdefault("rag_queries", 0)
        payload.setdefault("source_ids", [])
        payload.setdefault("model_version", DEFAULT_MODEL_VERSION)
        return self.log_event("turn", payload)

    def record_voice_timing(
        self,
        *,
        call_id: str,
        turn_id: str,
        speech_ended_at: Any,
        audio_started_at: Any,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """Record perceived browser voice latency as a separate event type.

        A timing callback is observability for an existing agent turn, not a new
        turn.  Keeping it separate prevents token, RAG, turn, and normal model
        latency totals from being counted a second time.
        """

        latency_ms = _timestamp_difference_ms(speech_ended_at, audio_started_at)
        payload: dict[str, Any] = {
            "call_id": str(call_id),
            "turn_id": str(turn_id),
            "speech_ended_at": speech_ended_at,
            "audio_started_at": audio_started_at,
            "latency_ms": latency_ms,
            "voice_latency_ms": latency_ms,
        }
        if created_at is not None:
            payload["created_at"] = created_at

        with self._lock:
            # Browser retries should not turn one spoken response into several
            # voice-latency samples.
            for existing in reversed(self.events()):
                if (
                    str(existing.get("event_type", existing.get("type", "")))
                    == "voice_timing"
                    and str(existing.get("call_id")) == str(call_id)
                    and str(existing.get("turn_id")) == str(turn_id)
                ):
                    return dict(existing)
            return self.log_event("voice_timing", payload)

    record_voice_latency = record_voice_timing

    def record_call(
        self,
        call_id: str,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model_calls: int = 0,
        rag_queries: int = 0,
        **extra: Any,
    ) -> dict[str, Any]:
        """Record an optional call-level summary event."""

        return self.log_event(
            "call",
            {
                "call_id": call_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model_calls": model_calls,
                "rag_queries": rag_queries,
                **extra,
            },
        )

    def _file_events(self) -> list[dict[str, Any]]:
        if self.log_path is None or not self.log_path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            with self.log_path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, dict):
                        events.append(value)
        except OSError:
            return []
        return events

    def events(self) -> list[dict[str, Any]]:
        """Read events, including events written by another process if present."""

        with self._lock:
            from_file = self._file_events()
            if from_file:
                return from_file
            return [dict(event) for event in self._memory_events]

    read_events = events

    def _database_events(self) -> list[dict[str, Any]]:
        if self.database is None:
            return []
        try:
            rows = self.database.execute(
                "SELECT id, call_id, latency_ms, input_tokens, output_tokens, "
                "model_calls, rag_queries, created_at FROM turns ORDER BY created_at, turn_index"
            ).fetchall()
        except Exception:
            return []
        return [
            {
                "event_type": "turn",
                "turn_id": str(row["id"]),
                "call_id": str(row["call_id"]),
                "latency_ms": row["latency_ms"],
                "input_tokens": row["input_tokens"] or 0,
                "output_tokens": row["output_tokens"] or 0,
                "model_calls": row["model_calls"] or 0,
                "rag_queries": row["rag_queries"] or 0,
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def aggregate(self, events: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
        """Compute P50/P95 and consumption totals from turn events."""

        source_events = list(events) if events is not None else self.events()
        def event_type(event: Mapping[str, Any]) -> str:
            return str(event.get("event_type", event.get("type", "turn")))

        turn_events = [
            event
            for event in source_events
            if event_type(event) == "turn"
        ]
        voice_events = [
            event
            for event in source_events
            if event_type(event) == "voice_timing"
        ]
        if not turn_events and events is None:
            turn_events = self._database_events()

        latencies: list[float] = []
        input_total = 0
        output_total = 0
        model_total = 0
        rag_total = 0
        per_call: dict[str, dict[str, Any]] = {}
        for event in turn_events:
            latency = event.get("latency_ms")
            if latency is None:
                latency = _timestamp_difference_ms(
                    event.get("speech_ended_at"), event.get("audio_started_at")
                )
            if latency is not None:
                try:
                    number = float(latency)
                except (TypeError, ValueError):
                    number = math.nan
                if math.isfinite(number):
                    latencies.append(number)

            def integer(name: str) -> int:
                try:
                    return max(0, int(event.get(name, 0) or 0))
                except (TypeError, ValueError):
                    return 0

            input_tokens = integer("input_tokens")
            output_tokens = integer("output_tokens")
            model_calls = integer("model_calls")
            rag_queries = integer("rag_queries")
            input_total += input_tokens
            output_total += output_tokens
            model_total += model_calls
            rag_total += rag_queries

            raw_call_id = event.get("call_id")
            if raw_call_id is None:
                continue
            call_id = str(raw_call_id)
            call = per_call.setdefault(
                call_id,
                {
                    "turns": 0,
                    "latencies_ms": [],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "model_calls": 0,
                    "rag_queries": 0,
                },
            )
            call["turns"] += 1
            if latency is not None:
                try:
                    if math.isfinite(float(latency)):
                        call["latencies_ms"].append(float(latency))
                except (TypeError, ValueError):
                    pass
            call["input_tokens"] += input_tokens
            call["output_tokens"] += output_tokens
            call["model_calls"] += model_calls
            call["rag_queries"] += rag_queries

        voice_latencies: list[float] = []
        voice_per_call: dict[str, list[float]] = {}
        for event in voice_events:
            latency = event.get("voice_latency_ms")
            if latency is None:
                latency = event.get("latency_ms")
            if latency is None:
                latency = _timestamp_difference_ms(
                    event.get("speech_ended_at"), event.get("audio_started_at")
                )
            try:
                number = float(latency) if latency is not None else math.nan
            except (TypeError, ValueError):
                number = math.nan
            if not math.isfinite(number):
                continue
            voice_latencies.append(number)
            raw_call_id = event.get("call_id")
            if raw_call_id is not None:
                voice_per_call.setdefault(str(raw_call_id), []).append(number)

        p50 = percentile(latencies, 50)
        p95 = percentile(latencies, 95)
        voice_p50 = percentile(voice_latencies, 50)
        voice_p95 = percentile(voice_latencies, 95)
        per_call_output: dict[str, dict[str, Any]] = {}
        for call_id, values in per_call.items():
            call_latencies = values.pop("latencies_ms")
            values["p50_ms"] = percentile(call_latencies, 50)
            values["p95_ms"] = percentile(call_latencies, 95)
            call_voice_latencies = voice_per_call.get(call_id, [])
            values["voice_latency_count"] = len(call_voice_latencies)
            values["voice_latency_p50_ms"] = percentile(call_voice_latencies, 50)
            values["voice_latency_p95_ms"] = percentile(call_voice_latencies, 95)
            per_call_output[call_id] = values

        result: dict[str, Any] = {
            "events": len(turn_events),
            "turns": len(turn_events),
            "calls": len(per_call_output),
            "latency_count": len(latencies),
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p50_ms": p50,
            "p95_ms": p95,
            "latency": {"count": len(latencies), "p50": p50, "p95": p95},
            "voice_events": len(voice_events),
            "voice_latency_count": len(voice_latencies),
            "voice_latency_p50_ms": voice_p50,
            "voice_latency_p95_ms": voice_p95,
            "voice_latency": {
                "count": len(voice_latencies),
                "p50": voice_p50,
                "p95": voice_p95,
            },
            "input_tokens": input_total,
            "output_tokens": output_total,
            "model_calls": model_total,
            "rag_queries": rag_total,
            "tokens": {"input": input_total, "output": output_total},
            "per_call": per_call_output,
        }
        return result

    metrics = aggregate
    summary = aggregate
    get_metrics = aggregate


def log_event(
    metrics: MetricsService,
    event_type: str,
    event: Mapping[str, Any] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Functional convenience wrapper for route/bootstrap integrations."""

    return metrics.log_event(event_type, event, **fields)


def calculate_metrics(
    events: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate an in-memory event collection without creating a file."""

    return MetricsService().aggregate(events)


__all__ = [
    "DEFAULT_MODEL_VERSION",
    "MetricsService",
    "calculate_metrics",
    "log_event",
    "percentile",
]
