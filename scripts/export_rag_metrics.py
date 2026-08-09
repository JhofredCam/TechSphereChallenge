"""Aggregate redacted RAG and voice spans from local JSONL events."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.services.metrics import percentile


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export reproducible RAG metrics from JSONL.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def export_metrics(path: Path) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rag = [row for row in rows if str(row.get("event_type")) in {"trace_span", "rag_query"}]
    latencies = [float(row["latency_ms"]) for row in rag if row.get("latency_ms") is not None]
    empty = sum(1 for row in rag if row.get("fallback_reason") in {"no_current_evidence", "empty"})
    fallback = sum(1 for row in rag if row.get("fallback_reason"))
    voice = [
        float(row.get("voice_latency_ms", row.get("latency_ms")))
        for row in rows
        if row.get("event_type") == "voice_timing"
        and row.get("voice_latency_ms", row.get("latency_ms")) is not None
    ]
    return {
        "schema_version": 1,
        "events_total": len(rows),
        "rag_requests_total": len(rag),
        "rag_query_latency_ms": {
            "count": len(latencies),
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
        },
        "rag_empty_total": empty,
        "rag_fallback_total": fallback,
        "voice_turn_e2e_latency_ms": {
            "count": len(voice),
            "p50": percentile(voice, 50),
            "p95": percentile(voice, 95),
        },
        "notes": ["Los campos ausentes no se convierten en latencia cero."],
    }


def main() -> int:
    args = _parser().parse_args()
    result = export_metrics(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
