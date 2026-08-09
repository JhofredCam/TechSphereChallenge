from __future__ import annotations

import json

from app.services.metrics import MetricsService, calculate_metrics, percentile


def test_metrics_write_jsonl_and_calculate_p50_p95(tmp_path):
    path = tmp_path / "events" / "turns.jsonl"
    metrics = MetricsService(log_path=path)
    for index, latency in enumerate((10, 20, 30, 40), start=1):
        metrics.record_turn(
            call_id="call-1" if index < 4 else "call-2",
            turn_id=f"turn-{index}",
            latency_ms=latency,
            input_tokens=index,
            output_tokens=2,
            model_calls=1,
            rag_queries=1,
            source_ids=[f"source-{index}"],
        )

    result = metrics.get_metrics()

    assert path.exists()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 4
    assert result["latency_p50_ms"] == 25
    assert result["latency_p95_ms"] == 38.5
    assert result["input_tokens"] == 10
    assert result["output_tokens"] == 8
    assert result["model_calls"] == 4
    assert result["rag_queries"] == 4
    assert result["calls"] == 2
    json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def test_metrics_can_derive_latency_from_timestamps_and_work_in_memory():
    metrics = MetricsService()
    metrics.record_turn(
        call_id="call-1",
        turn_id="turn-1",
        speech_ended_at="2026-01-01T00:00:00+00:00",
        audio_started_at="2026-01-01T00:00:00.250000+00:00",
    )

    result = metrics.aggregate()

    assert result["latency_p50_ms"] == 250
    assert percentile([1, 2, 3], 95) == 2.9
    assert calculate_metrics([])["latency_p95_ms"] is None


def test_voice_timing_is_aggregated_separately_from_turn_metrics():
    metrics = MetricsService()
    metrics.record_turn(
        call_id="call-1",
        turn_id="turn-1",
        latency_ms=20,
        input_tokens=4,
        output_tokens=5,
        model_calls=1,
        rag_queries=1,
    )
    metrics.record_voice_timing(
        call_id="call-1",
        turn_id="turn-1",
        speech_ended_at="2026-01-01T00:00:00+00:00",
        audio_started_at="2026-01-01T00:00:00.300000+00:00",
    )

    result = metrics.aggregate()

    assert result["events"] == 1
    assert result["turns"] == 1
    assert result["voice_events"] == 1
    assert result["latency_count"] == 1
    assert result["latency_p50_ms"] == 20
    assert result["voice_latency_count"] == 1
    assert result["voice_latency_p50_ms"] == 300
    assert result["input_tokens"] == 4
    assert result["output_tokens"] == 5
    assert result["model_calls"] == 1
    assert result["rag_queries"] == 1


def test_metrics_do_not_fabricate_latency_from_invalid_or_reversed_timestamps():
    metrics = MetricsService()
    metrics.record_turn(
        call_id="call-invalid",
        turn_id="turn-invalid",
        speech_ended_at="not-a-timestamp",
        audio_started_at="still-not-a-timestamp",
    )
    metrics.record_voice_timing(
        call_id="call-invalid",
        turn_id="turn-invalid",
        speech_ended_at="2026-01-01T00:00:01+00:00",
        audio_started_at="2026-01-01T00:00:00+00:00",
    )

    result = metrics.aggregate()

    assert result["latency_count"] == 0  # UT-MET-01
    assert result["latency_p50_ms"] is None
    assert result["latency_p95_ms"] is None
    assert result["voice_latency_count"] == 0


def test_percentile_ignores_nonfinite_values_and_clamps_boundaries():
    assert percentile([float("nan"), 2, float("inf"), 4], 0) == 2
    assert percentile([2, 4], 50) == 3
    assert percentile([2, 4], 100) == 4
