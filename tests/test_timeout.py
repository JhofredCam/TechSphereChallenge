from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import (
    DEFAULT_PATIENT_LISTEN_TIMEOUT_MS,
    MAX_PATIENT_LISTEN_TIMEOUT_MS,
    MIN_PATIENT_LISTEN_TIMEOUT_MS,
    Settings,
)
from app.database import init_database
from app.main import create_app
from app.services.calls import CallService, LateTranscriptError


def _http_client(tmp_path, *, timeout_ms=DEFAULT_PATIENT_LISTEN_TIMEOUT_MS):
    settings = Settings(data_dir=tmp_path, patient_listen_timeout_ms=timeout_ms)
    database = init_database(settings)
    application = create_app(settings=settings, database=database)
    return TestClient(application), settings, database


@pytest.mark.parametrize(
    "value",
    ["", " ", "abc", "0", "-1", "999", "300001", "1.5"],
)
def test_patient_listen_timeout_rejects_invalid_environment_values(tmp_path, value):
    with pytest.raises(ValueError, match="PATIENT_LISTEN_TIMEOUT_MS"):
        Settings.from_env(
            {"PATIENT_LISTEN_TIMEOUT_MS": value},
            project_root=tmp_path,
        )


def test_patient_listen_timeout_default_boundaries_and_direct_settings_validation(tmp_path):
    assert (
        Settings.from_env({}, project_root=tmp_path).patient_listen_timeout_ms
        == DEFAULT_PATIENT_LISTEN_TIMEOUT_MS
    )
    assert (
        Settings.from_env(
            {"PATIENT_LISTEN_TIMEOUT_MS": str(MIN_PATIENT_LISTEN_TIMEOUT_MS)},
            project_root=tmp_path,
        ).patient_listen_timeout_ms
        == MIN_PATIENT_LISTEN_TIMEOUT_MS
    )
    assert (
        Settings.from_env(
            {"PATIENT_LISTEN_TIMEOUT_MS": str(MAX_PATIENT_LISTEN_TIMEOUT_MS)},
            project_root=tmp_path,
        ).patient_listen_timeout_ms
        == MAX_PATIENT_LISTEN_TIMEOUT_MS
    )
    with pytest.raises(ValueError, match="patient_listen_timeout_ms"):
        Settings(data_dir=tmp_path, patient_listen_timeout_ms=0)
    with pytest.raises(ValueError, match="patient_listen_timeout_ms"):
        Settings(data_dir=tmp_path, patient_listen_timeout_ms="30000")  # type: ignore[arg-type]


def test_health_exposes_effective_timeout_without_changing_provider_or_sqlite_timeouts(tmp_path):
    client, settings, database = _http_client(tmp_path, timeout_ms=45_000)

    health = client.get("/health")

    assert health.status_code == 200
    assert health.json()["patient_listen_timeout_ms"] == 45_000
    assert client.app.state.agent.timeout == 12.0
    assert client.app.state.voice.timeout == 30.0
    assert database.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert "GROQ_API_KEY" not in json.dumps(health.json())
    assert settings.patient_listen_timeout_ms == 45_000


def test_voice_events_are_bounded_and_timeout_creates_no_clinical_turn(tmp_path):
    client, settings, database = _http_client(tmp_path, timeout_ms=1_000)
    call = client.post("/api/calls", json={"name": "Ana"}).json()
    ids = {"listen_id": "listen_timeout_1", "client_turn_id": "client_timeout_1"}
    event_base = {
        **ids,
        "configured_timeout_ms": 1_000,
        "elapsed_ms": 1_000,
        "locale": "es-CO",
        "implementation": "SpeechRecognition",
    }

    started = client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={"event_type": "patient_listen_started", **event_base},
    )
    partial = client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={"event_type": "partial", **event_base},
    )
    timed_out = client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={"event_type": "timeout", **event_base},
    )

    assert started.status_code == 200
    assert partial.status_code == 200
    assert timed_out.status_code == 200
    assert timed_out.json()["status"] == "LISTEN_TIMEOUT"
    assert client.get(f"/api/calls/{call['id']}").json()["turns"] == []
    attempt = database.execute(
        "SELECT status, configured_timeout_ms FROM listening_attempts WHERE listen_id = ?",
        (ids["listen_id"],),
    ).fetchone()
    assert tuple(attempt) == ("LISTEN_TIMEOUT", 1_000)

    late = client.post(
        f"/api/calls/{call['id']}/turns",
        json={"text": "Tengo dolor", **ids, "elapsed_ms": 1_000},
    )
    assert late.status_code == 409
    assert late.json()["detail"]["error_code"] == "late_transcript"
    assert client.get(f"/api/calls/{call['id']}").json()["turns"] == []
    assert client.get(f"/api/calls/{call['id']}").json()["status"] == "active"

    lines = settings.data_dir.joinpath("events.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    timeout_events = [event for event in events if event["event_type"] == "timeout"]
    assert timeout_events
    assert timeout_events[-1]["call_id"] == call["id"]
    assert timeout_events[-1]["listen_id"] == ids["listen_id"]
    assert timeout_events[-1]["client_turn_id"] == ids["client_turn_id"]
    assert timeout_events[-1]["configured_timeout_ms"] == 1_000
    assert "text" not in timeout_events[-1]
    assert "GROQ_API_KEY" not in json.dumps(events)
    assert "Tengo dolor" not in json.dumps(events)


def test_no_response_stays_outside_turns_and_event_contract_rejects_clinical_fields(tmp_path):
    client, _, database = _http_client(tmp_path)
    call = client.post("/api/calls", json={"name": "Ana"}).json()

    started = client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={"event_type": "patient_listen_started", "listen_id": "listen_no_response"},
    )
    ended = client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={
            "event_type": "no_response",
            "listen_id": "listen_no_response",
            "elapsed_ms": 500,
        },
    )
    forbidden_text = client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={
            "event_type": "partial",
            "listen_id": "listen_no_response",
            "text": "secreto clinico",
        },
    )
    forbidden_type = client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={"event_type": "patient_listen_partial", "listen_id": "listen_bad"},
    )

    assert started.status_code == 200
    assert ended.status_code == 200
    assert ended.json()["status"] == "NO_RESPONSE"
    assert forbidden_text.status_code == 422
    assert forbidden_type.status_code == 422
    assert database.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 0


def test_exact_deadline_is_accepted_before_timeout_event(tmp_path):
    client, _, database = _http_client(tmp_path, timeout_ms=1_000)
    call = client.post("/api/calls", json={"name": "Ana"}).json()
    ids = {"listen_id": "listen_deadline", "client_turn_id": "client_deadline"}
    base = {**ids, "configured_timeout_ms": 1_000, "elapsed_ms": 1_000}

    assert client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={"event_type": "patient_listen_started", **base},
    ).status_code == 200
    final = client.post(
        f"/api/calls/{call['id']}/voice-events",
        json={"event_type": "final", **base},
    )
    accepted = client.post(
        f"/api/calls/{call['id']}/turns",
        json={"text": "Estoy bien", **ids, "elapsed_ms": 1_000},
    )

    assert final.status_code == 200
    assert final.json()["status"] == "FINAL_RECEIVED"
    assert accepted.status_code == 200
    assert accepted.json()["duplicate"] is False
    assert database.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 2


def test_same_client_turn_id_returns_persisted_result_without_model_or_metric_duplicates(tmp_path):
    database = init_database(Settings(data_dir=tmp_path))
    calls_run = []

    class CountingAgent:
        def respond(self, text, **kwargs):
            calls_run.append(text)
            return {"text": "Respuesta segura.", "sources": []}

    calls = CallService(database, agent=CountingAgent())
    call = calls.start_call(patient_id="patient-1", procedure="hernia")
    first = calls.handle_turn(
        call["id"],
        "Estoy bien",
        client_turn_id="client_once",
        listen_id="listen_once",
    )
    second = calls.handle_turn(
        call["id"],
        "Estoy bien",
        client_turn_id="client_once",
        listen_id="listen_once",
    )

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["patient_turn_id"] == first["patient_turn_id"]
    assert second["agent_turn_id"] == first["agent_turn_id"]
    assert len(calls_run) == 1
    assert database.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 2
    assert calls.metrics.aggregate()["events"] == 2

    other_call = calls.start_call(patient_id="patient-2", procedure="hernia")
    with pytest.raises(ValueError, match="client_turn_id_not_for_call"):
        calls.handle_turn(
            other_call["id"],
            "Estoy bien",
            client_turn_id="client_once",
            listen_id="listen_other",
        )


def test_service_timeout_wins_and_late_transcript_does_not_create_turn(tmp_path):
    database = init_database(Settings(data_dir=tmp_path))
    calls = CallService(database, configured_timeout_ms=1_000)
    call = calls.start_call(patient_id="patient-1", procedure="hernia")
    calls.record_voice_event(
        call["id"],
        event_type="patient_listen_started",
        listen_id="listen_race",
        client_turn_id="client_race",
        configured_timeout_ms=1_000,
    )
    calls.record_voice_event(
        call["id"],
        event_type="timeout",
        listen_id="listen_race",
        client_turn_id="client_race",
        elapsed_ms=1_000,
        configured_timeout_ms=1_000,
    )

    with pytest.raises(LateTranscriptError):
        calls.handle_turn(
            call["id"],
            "Llegue tarde",
            client_turn_id="client_race",
            listen_id="listen_race",
            elapsed_ms=1_000,
        )

    assert calls.list_turns(call["id"]) == []
    assert database.execute(
        "SELECT status FROM listening_attempts WHERE listen_id = ?", ("listen_race",)
    ).fetchone()[0] == "LISTEN_TIMEOUT"


def test_voice_event_retries_are_isolated_per_attempt(tmp_path):
    client, _, database = _http_client(tmp_path)
    first_call = client.post("/api/calls", json={"name": "Ana"}).json()
    second_call = client.post("/api/calls", json={"name": "Luis"}).json()

    first = client.post(
        f"/api/calls/{first_call['id']}/voice-events",
        json={
            "event_type": "patient_listen_started",
            "listen_id": "same_listen_name",
            "client_turn_id": "same_client_name",
        },
    )
    second = client.post(
        f"/api/calls/{second_call['id']}/voice-events",
        json={
            "event_type": "patient_listen_started",
            "listen_id": "same_listen_name",
            "client_turn_id": "same_client_name",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"]["error_code"] in {
        "client_turn_id_not_for_call",
        "listen_id_not_for_call",
    }
    assert database.execute("SELECT COUNT(*) FROM listening_attempts").fetchone()[0] == 1


def test_server_timeout_setting_is_not_read_from_browser_source():
    source = Path("app/web/app.js").read_text(encoding="utf-8")
    assert ".env" not in source
    assert 'api("/health")' in source
    assert "performance.now()" in source
    assert "interimResults = true" in source
