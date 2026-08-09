from __future__ import annotations

import pytest

from app.services.voice import VoiceService, VoiceUnavailable


class FakeResponse:
    def __init__(self, payload=None, error: Exception | None = None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeHttpClient:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def test_voice_service_uses_fake_provider_contract_without_network():
    client = FakeHttpClient(FakeResponse({"text": "Transcripcion local de prueba."}))
    service = VoiceService(
        api_key="test-key",
        model="whisper-test",
        endpoint="https://provider.invalid/transcribe",
        timeout=4.5,
        http_client=client,
    )

    transcript = service.transcribe(
        b"audio-bytes",
        filename="turn.webm",
        content_type="audio/webm",
    )

    assert transcript == "Transcripcion local de prueba."
    assert len(client.calls) == 1  # IT-VOICE-01: the provider boundary is fake and local.
    args, kwargs = client.calls[0]
    assert args == ("https://provider.invalid/transcribe",)
    assert kwargs["headers"] == {"Authorization": "Bearer test-key"}
    assert kwargs["data"] == {"model": "whisper-test", "response_format": "json"}
    assert kwargs["files"]["file"] == ("turn.webm", b"audio-bytes", "audio/webm")
    assert kwargs["timeout"] == 4.5


def test_voice_service_rejects_unconfigured_empty_and_oversized_audio():
    with pytest.raises(VoiceUnavailable, match="GROQ_API_KEY"):
        VoiceService(api_key="").transcribe(b"audio")

    service = VoiceService(
        api_key="test-key",
        max_bytes=3,
        http_client=FakeHttpClient(FakeResponse()),
    )
    with pytest.raises(ValueError, match="vacio"):
        service.transcribe(b"")
    with pytest.raises(ValueError, match="supera el limite"):
        service.transcribe(b"1234")


def test_voice_service_converts_provider_errors_and_empty_payloads_to_safe_errors():
    failed_client = FakeHttpClient(FakeResponse(error=RuntimeError("provider down")))
    with pytest.raises(VoiceUnavailable, match="no fue posible transcribir"):
        VoiceService(api_key="test-key", http_client=failed_client).transcribe(b"audio")

    for payload in (RuntimeError("invalid json"), {}, {"text": "  "}, []):
        client = FakeHttpClient(FakeResponse(payload))
        with pytest.raises(VoiceUnavailable):
            VoiceService(api_key="test-key", http_client=client).transcribe(b"audio")
