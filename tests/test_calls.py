from __future__ import annotations

import json

from app.database import init_database
from app.services.calls import CallService
from app.services.triage import classify_triage


def test_calls_persist_turn_sources_and_conservative_closing_summary(tmp_path):
    database = init_database(tmp_path / "app.sqlite3")
    calls = CallService(database)
    call = calls.start_call(patient_id="patient-1", procedure="colecistectomia")

    first = calls.record_turn(
        call.id,
        "patient",
        "Me falta el aire",
        triage=classify_triage("Me falta el aire"),
        sources=[
            {
                "citation": "protocolo.txt (p. 2)",
                "page_number": 2,
                "score": 0.9,
                "corpus_revision": 1,
            }
        ],
        latency_ms=123.5,
        input_tokens=12,
        output_tokens=8,
        model_calls=0,
        rag_queries=1,
    )
    calls.record_turn(
        call.id,
        "agent",
        "Busque atencion inmediata.",
        triage_level="green",
    )

    stored_call = calls.get_call(call.id)
    stored_sources = calls.get_sources(call_id=call.id)
    closed = calls.close_call(
        call.id,
        symptoms=["dificultad para respirar"],
        next_steps=["Contactar urgencias"],
    )

    assert first.sources[0].citation == "protocolo.txt (p. 2)"
    assert stored_call.triage_level == "red"
    assert stored_call.alert is True
    assert len(calls.list_turns(call.id)) == 2
    assert len(stored_sources) == 1
    assert closed.status == "closed"
    assert closed.triage_level == "red"
    assert closed.summary["patient"] == "patient-1"
    assert closed.summary["procedure"] == "colecistectomia"
    assert closed.summary["symptoms"] == ["dificultad para respirar"]
    assert closed.summary["decision"] == "red"
    assert closed.summary["sources"]
    assert closed.summary["alert"] is True
    assert closed.summary["next_steps"] == ["Contactar urgencias"]
    json.dumps(closed)


def test_handle_turn_persists_agent_metrics_and_source_links(tmp_path):
    database = init_database(tmp_path / "app.sqlite3")
    response = {
        "text": "La fuente indica vigilancia.",
        "sources": [{"citation": "guia.txt (p. 1)", "page_number": 1}],
        "metrics": {
            "latency_ms": 12,
            "input_tokens": 5,
            "output_tokens": 6,
            "model_calls": 0,
            "rag_queries": 1,
            "model_version": "llama-3.1-8b-instant",
        },
    }

    class FakeAgent:
        def respond(self, message, **kwargs):
            return response

    calls = CallService(database, agent=FakeAgent())
    call = calls.start_call("p-2", "hernia")
    result = calls.handle_turn(call.id, "Estoy bien")

    turns = calls.list_turns(call.id)
    assert result.patient_turn_id == turns[0].id
    assert result.agent_turn_id == turns[1].id
    assert turns[1].rag_queries == 1
    assert calls.get_sources(turn_id=turns[1].id)[0].citation == "guia.txt (p. 1)"


def test_voice_timing_belongs_to_an_agent_turn_and_is_idempotent(tmp_path):
    database = init_database(tmp_path / "app.sqlite3")

    class FakeAgent:
        def respond(self, message, **kwargs):
            return {"text": "Respuesta local.", "sources": []}

    calls = CallService(database, agent=FakeAgent())
    call = calls.start_call("p-3", "hernia")
    result = calls.handle_turn(call.id, "Estoy bien")

    timing = calls.record_voice_timing(
        call.id,
        result.agent_turn_id,
        speech_ended_at="2026-01-01T00:00:00+00:00",
        audio_started_at="2026-01-01T00:00:00.125000+00:00",
    )
    repeated = calls.record_voice_timing(
        call.id,
        result.agent_turn_id,
        speech_ended_at="2026-01-01T00:00:00+00:00",
        audio_started_at="2026-01-01T00:00:00.125000+00:00",
    )

    assert timing.voice_latency_ms == 125
    assert repeated == timing
    assert calls.metrics.aggregate()["turns"] == 2
    assert calls.metrics.aggregate()["voice_events"] == 1
