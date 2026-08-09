from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app


@pytest.fixture
def http_context(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    application = create_app(settings=settings, database=database)
    with TestClient(application) as client:
        yield client, database
    database.close()


def test_http_call_and_turn_limits_are_rejected_and_close_is_not_repeated(http_context):
    client, _ = http_context

    assert client.post("/api/calls", json={}).status_code == 422
    assert client.get("/api/calls/missing-call").status_code == 404
    started = client.post("/api/calls", json={"name": "Ana"})
    assert started.status_code == 200
    call_id = started.json()["id"]

    assert client.post(
        f"/api/calls/{call_id}/turns", json={"text": "x" * 5001}
    ).status_code == 422
    assert client.post(
        f"/api/calls/{call_id}/turns", json={"text": "ok", "client_turn_id": "only-one"}
    ).status_code == 422
    assert client.post(
        f"/api/calls/{call_id}/turns", json={"text": "ok", "unexpected": True}
    ).status_code == 422

    turn = client.post(f"/api/calls/{call_id}/turns", json={"text": "Estoy bien"})
    assert turn.status_code == 200
    finished = client.post(f"/api/calls/{call_id}/finish", json={})
    assert finished.status_code == 200
    repeated = client.post(f"/api/calls/{call_id}/finish", json={})
    assert repeated.status_code == 409


def test_http_pages_are_available_without_exposing_internal_storage(http_context):
    client, _ = http_context

    for path in ("/", "/admin", "/call"):
        response = client.get(path)
        assert response.status_code == 200
        assert "stored_path" not in response.text

    uploaded = client.post(
        "/api/admin/documents",
        files={"file": ("broken.pdf", b"not a pdf", "application/pdf")},
    )
    assert uploaded.status_code == 200
    payload = uploaded.json()
    assert payload["status"] == "error"
    assert payload["enabled"] is False
    assert payload["rag_eligible"] is False
    assert payload["page_count"] == 0
    assert "stored_path" not in payload  # IT-HTTP-01: API payloads stay path-free.


def test_http_voice_events_reject_invalid_contract_values_without_clinical_text(http_context):
    client, _ = http_context
    call = client.post("/api/calls", json={"name": "Ana"}).json()
    endpoint = f"/api/calls/{call['id']}/voice-events"

    assert client.post(
        endpoint,
        json={"event_type": "final", "listen_id": "listen-1"},
    ).status_code == 422
    assert client.post(
        endpoint,
        json={"event_type": "partial", "listen_id": "listen-2", "locale": "en-US"},
    ).status_code == 422
    mismatched = client.post(
        endpoint,
        json={
            "event_type": "patient_listen_started",
            "listen_id": "listen-3",
            "configured_timeout_ms": 1_000,
        },
    )
    assert mismatched.status_code == 409
    assert mismatched.json()["detail"]["error_code"] == "timeout_configuration_mismatch"
