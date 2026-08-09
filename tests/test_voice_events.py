from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app


def test_vad_events_are_bounded_and_do_not_contain_audio_or_text(tmp_path):
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    application = create_app(settings=settings, database=database)
    try:
        with TestClient(application) as client:
            call = client.post("/api/calls", json={"name": "Demo"}).json()
            endpoint = f"/api/calls/{call['id']}/voice-events"
            base = {
                "listen_id": "listen-vad-1",
                "locale": "es-CO",
                "implementation": "SpeechRecognition",
                "silence_timeout_ms": 2000,
            }
            event_types = ("vad_speech_started", "vad_silence_started", "vad_segment_finalized")
            for event_type in event_types:
                response = client.post(endpoint, json={**base, "event_type": event_type})
                assert response.status_code == 200
            health = client.get("/health")
            assert health.status_code == 200
            payload = health.json()
            assert payload["voice_silence_timeout_ms"] == 2000
            assert payload["voice_vad_rms_threshold"] == 0.025
            assert payload["voice_speech_start_timeout_ms"] == 10000
            assert "audio" not in response.text.lower()
            assert "transcript" not in response.text.lower()
    finally:
        database.close()
