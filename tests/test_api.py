from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    return TestClient(create_app(settings=settings, database=database))


def test_health_exposes_local_capabilities(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model_family"] == "Meta Llama"
    assert payload["model_id"] == "llama-3.1-8b-instant"
    assert payload["fts5"] is True
    assert payload["docs_count"] == 0
    assert payload["voice_mode"] == "browser-speechrecognition"
    assert payload["llm_configured"] is False
    assert payload["llm_provider"] == "extractive"
    assert payload["llm_status"] == "fallback_only"
    assert "GROQ_API_KEY" not in json.dumps(payload)


def test_explicit_settings_do_not_inherit_provider_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "process-key")
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    application = create_app(settings=settings, database=database)

    payload = TestClient(application).get("/health").json()

    assert payload["llm_configured"] is False
    assert payload["llm_status"] == "fallback_only"
    assert payload["voice_mode"] == "browser-speechrecognition"


def test_document_crud_reports_available_and_forgets_source(client):
    uploaded = client.post(
        "/api/admin/documents",
        files={"file": ("guia.txt", b"La recuperacion lunaria requiere vigilancia.", "text/plain")},
    )

    assert uploaded.status_code == 200
    document = uploaded.json()
    assert document["status"] == "available"
    assert document["available"] is True

    listed = client.get("/api/admin/documents")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    document_id = document["id"]

    deleted = client.delete(f"/api/admin/documents/{document_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert client.get("/api/admin/documents").json()["documents"] == []


def test_http_g5_upload_use_delete_and_forget_without_restart(client):
    marker = "mariposa zafiro 92817"
    uploaded = client.post(
        "/api/admin/documents",
        files={
            "file": (
                "g5-unique.txt",
                f"La clave de seguimiento {marker} indica revisar el vendaje cada manana.",
                "text/plain",
            )
        },
    )
    assert uploaded.status_code == 200
    document_id = uploaded.json()["id"]

    first_call = client.post("/api/calls", json={"name": "Ana"}).json()
    question = f"Que indica la clave de seguimiento {marker}?"
    before_delete = client.post(
        f"/api/calls/{first_call['id']}/turns",
        json={"text": question},
    )
    assert before_delete.status_code == 200
    before_payload = before_delete.json()
    assert before_payload["grounded"] is True
    assert before_payload["abstained"] is False
    assert before_payload["sources"]
    assert marker in before_payload["sources"][0]["text"]

    deleted = client.delete(f"/api/admin/documents/{document_id}")
    assert deleted.status_code == 200

    second_call = client.post("/api/calls", json={"name": "Ana"}).json()
    after_delete = client.post(
        f"/api/calls/{second_call['id']}/turns",
        json={"text": question},
    )
    assert after_delete.status_code == 200
    after_payload = after_delete.json()
    assert after_payload["abstained"] is True
    assert after_payload["grounded"] is False
    assert after_payload["sources"] == []


def test_document_upload_rejects_extension_and_size(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = Settings(data_dir=tmp_path, max_upload_bytes=4)
    database = init_database(settings)
    client = TestClient(create_app(settings=settings, database=database))

    unsupported = client.post(
        "/api/admin/documents",
        files={"file": ("guide.csv", b"abcd", "text/csv")},
    )
    oversized = client.post(
        "/api/admin/documents",
        files={"file": ("guide.txt", b"12345", "text/plain")},
    )

    assert unsupported.status_code == 415
    assert "extension" in unsupported.json()["detail"]
    assert oversized.status_code == 413
    assert "limite" in oversized.json()["detail"]


def test_call_turn_and_finish_persist_triage_transcript_and_summary(client):
    started = client.post(
        "/api/calls",
        json={
            "patient_id": "pac-1",
            "name": "Ana",
            "procedure": "colecistectomia",
            "day_postop": 3,
        },
    )
    assert started.status_code == 200
    call = started.json()
    assert call["name"] == "Ana"
    assert call["day_postop"] == 3

    turn = client.post(
        f"/api/calls/{call['id']}/turns",
        json={"text": "Me falta el aire"},
    )
    assert turn.status_code == 200
    turn_payload = turn.json()
    assert turn_payload["triage"]["level"] == "red"
    assert turn_payload["alert"] is True
    assert turn_payload["text"]

    finished = client.post(
        f"/api/calls/{call['id']}/finish",
        json={"symptoms": ["dificultad para respirar"]},
    )
    assert finished.status_code == 200
    summary = finished.json()["summary"]
    assert finished.json()["status"] == "closed"
    assert summary["patient_id"] == "pac-1"
    assert summary["procedure"] == "colecistectomia"
    assert summary["symptoms"] == ["dificultad para respirar"]
    assert summary["decision"] == "red"
    assert summary["alert"] is True
    assert summary["name"] == "Ana"
    assert summary["day_postop"] == 3


def test_voice_timing_route_records_real_latency_without_extra_turn(client):
    started = client.post(
        "/api/calls",
        json={"name": "Ana", "procedure": "hernia", "day_postop": 2},
    ).json()
    turn = client.post(
        f"/api/calls/{started['id']}/turns",
        json={"text": "Estoy bien"},
    ).json()

    timing = client.post(
        f"/api/calls/{started['id']}/turns/{turn['agent_turn_id']}/voice-timing",
        json={
            "speech_ended_at": "2026-01-01T00:00:00+00:00",
            "audio_started_at": "2026-01-01T00:00:00.250000+00:00",
        },
    )
    assert timing.status_code == 200
    assert timing.json()["recorded"] is True
    assert timing.json()["voice_latency_ms"] == 250

    metrics = client.get("/api/metrics")
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["events"] == 2
    assert payload["turns"] == 2
    assert payload["voice_events"] == 1
    assert payload["voice_latency_count"] == 1
    assert payload["voice_latency_p50_ms"] == 250


def test_audio_returns_local_fallback_without_network(client):
    started = client.post("/api/calls", json={"name": "Ana"}).json()

    response = client.post(
        f"/api/calls/{started['id']}/audio",
        files={"audio": ("turn.webm", b"not-a-real-audio", "audio/webm")},
    )

    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]
