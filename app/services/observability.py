"""Privacy-first local spans with an optional best-effort external exporter."""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Protocol

SENSITIVE_KEYS = frozenset(
    {
        "name",
        "patient_id",
        "procedure",
        "text",
        "transcript",
        "audio",
        "prompt",
        "prompt_text",
        "content",
        "chunk_text",
        "api_key",
        "authorization",
        "token",
        "password",
    }
)
PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\|/)[^\s]+")


def short_hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def redact_for_external(value: Any, *, key: str | None = None) -> Any:
    """Remove content/PII and hash correlators before an external exporter."""

    if key and key.casefold() in SENSITIVE_KEYS:
        return "[redacted]"
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            name = str(raw_key)
            normalized = name.casefold()
            if normalized in {"call_id", "turn_id", "trace_id", "run_id", "retrieval_id"}:
                result[f"{name}_hash"] = short_hash(raw_value)
            elif normalized in SENSITIVE_KEYS or "secret" in normalized or "key" in normalized:
                result[name] = "[redacted]"
            else:
                result[name] = redact_for_external(raw_value, key=name)
        return result
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact_for_external(item) for item in value]
    if isinstance(value, str):
        return PATH_PATTERN.sub("[path-redacted]", value)
    return value


@dataclass(frozen=True, slots=True)
class SpanEvent:
    name: str
    status: str
    latency_ms: float
    attributes: Mapping[str, Any]

    def external(self) -> dict[str, Any]:
        return {
            "span_name": self.name,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 3),
            "attributes": redact_for_external(self.attributes),
        }


class TraceExporter(Protocol):
    def send(self, event: Mapping[str, Any]) -> None: ...


class NoopTraceExporter:
    def send(self, event: Mapping[str, Any]) -> None:
        return None


class TraceRecorder:
    """Record local events and never let exporter failure affect the request."""

    def __init__(
        self,
        local_logger: Any | None = None,
        exporter: TraceExporter | None = None,
    ) -> None:
        self.local_logger = local_logger
        self.exporter = exporter or NoopTraceExporter()
        self.export_errors = 0

    def record(self, event: SpanEvent, *, correlation: Mapping[str, Any] | None = None) -> None:
        attributes = dict(correlation or {})
        attributes.update(event.attributes)
        local = {
            "event_type": "trace_span",
            "trace_id": attributes.get("trace_id", f"trace_{uuid.uuid4().hex}"),
            "span_name": event.name,
            "status": event.status,
            "latency_ms": round(event.latency_ms, 3),
            **attributes,
        }
        if self.local_logger is not None:
            self.local_logger.log_event("trace_span", local)
        try:
            self.exporter.send(event.external())
        except Exception:
            self.export_errors += 1

    @contextmanager
    def span(
        self,
        name: str,
        *,
        correlation: Mapping[str, Any] | None = None,
        attributes: Mapping[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        started = time.perf_counter()
        metadata: dict[str, Any] = dict(attributes or {})
        try:
            yield metadata
        except Exception as error:
            self.record(
                SpanEvent(
                    name,
                    "error",
                    (time.perf_counter() - started) * 1000,
                    {**metadata, "error_class": type(error).__name__},
                ),
                correlation=correlation,
            )
            raise
        else:
            self.record(
                SpanEvent(name, "ok", (time.perf_counter() - started) * 1000, metadata),
                correlation=correlation,
            )


__all__ = [
    "NoopTraceExporter",
    "SpanEvent",
    "TraceExporter",
    "TraceRecorder",
    "redact_for_external",
    "short_hash",
]
