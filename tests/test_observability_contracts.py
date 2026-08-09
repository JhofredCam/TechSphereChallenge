from __future__ import annotations

import json

from app.services.observability import TraceRecorder, redact_for_external
from scripts.check_observability import check
from scripts.export_rag_metrics import export_metrics


def test_external_redaction_hashes_correlators_and_removes_content():
    value = redact_for_external(
        {
            "call_id": "call-secret",
            "patient_id": "pac-001",
            "procedure": "apendicectomía",
            "prompt": "texto clínico",
            "path": "C:\\private\\source.pdf",
            "latency_ms": 12,
        }
    )
    assert "call_id" not in value
    assert value["call_id_hash"]
    assert value["patient_id"] == "[redacted]"
    assert value["procedure"] == "[redacted]"
    assert value["latency_ms"] == 12
    assert "private" not in value["path"]


def test_exporter_failure_is_best_effort_and_local_event_survives():
    local: list[dict[str, object]] = []

    class FailingExporter:
        def send(self, _event):
            raise RuntimeError("offline")

    class Logger:
        def log_event(self, _name, event):
            local.append(event)

    recorder = TraceRecorder(Logger(), FailingExporter())
    with recorder.span(
        "rag.retrieve",
        correlation={"call_id": "call-1"},
        attributes={"status": "ok"},
    ):
        pass
    assert recorder.export_errors == 1
    assert local[0]["span_name"] == "rag.retrieve"


def test_observability_defaults_off_and_export_omits_missing_latency(tmp_path):
    config = check({"APP_DATA_DIR": str(tmp_path)})
    assert config["langsmith_enabled"] is False
    events = tmp_path / "events.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps({"event_type": "trace_span", "latency_ms": 100}),
                json.dumps({"event_type": "trace_span"}),
                json.dumps({"event_type": "voice_timing", "voice_latency_ms": 50}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    exported = export_metrics(events)
    assert exported["rag_query_latency_ms"]["p50"] == 100
    assert exported["voice_turn_e2e_latency_ms"]["p95"] == 50
