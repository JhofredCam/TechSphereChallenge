"""Optional Groq Whisper transcription for browser/API calls.

The browser SpeechRecognition path is the default because it needs no provider
credentials.  This module only makes a remote request when ``GROQ_API_KEY`` is
configured; callers can therefore keep the local text fallback available.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_WHISPER_MODEL = "whisper-large-v3"


class VoiceUnavailable(RuntimeError):
    """Raised when server-side transcription is not configured or available."""


class VoiceService:
    """Transcribe audio through the optional Groq Whisper-compatible endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        endpoint: str | None = None,
        timeout: float = 30.0,
        max_bytes: int = 25 * 1024 * 1024,
        http_client: Any | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or os.getenv("GROQ_WHISPER_MODEL") or DEFAULT_WHISPER_MODEL
        self.endpoint = endpoint or os.getenv("GROQ_WHISPER_URL") or GROQ_WHISPER_URL
        self.timeout = timeout
        self.max_bytes = max(1, int(max_bytes))
        self.http_client = http_client

    def _configured_api_key(self) -> str | None:
        value = self.api_key if self.api_key is not None else os.getenv("GROQ_API_KEY")
        value = (value or "").strip()
        return value or None

    @property
    def mode(self) -> str:
        """Return the active server/browser voice mode for health and the UI."""

        return "groq-whisper" if self._configured_api_key() else "browser-speechrecognition"

    def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = "audio.webm",
        content_type: str | None = None,
    ) -> str:
        """Transcribe one audio payload or raise a clear, user-facing error."""

        api_key = self._configured_api_key()
        if api_key is None:
            raise VoiceUnavailable(
                "La transcripcion de audio del servidor no esta configurada. "
                "Use el boton de microfono con SpeechRecognition en Chrome o Edge, "
                "o configure GROQ_API_KEY para habilitar Whisper."
            )

        if not audio:
            raise ValueError("el archivo de audio esta vacio")
        if len(audio) > self.max_bytes:
            raise ValueError(f"el audio supera el limite de {self.max_bytes} bytes")

        client = self.http_client
        if client is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - dependency is declared
                raise VoiceUnavailable("httpx es necesario para la transcripcion remota") from exc
        else:
            httpx = None

        headers = {"Authorization": f"Bearer {api_key}"}
        files = {
            "file": (
                filename or "audio.webm",
                audio,
                content_type or "application/octet-stream",
            )
        }
        data = {"model": self.model, "response_format": "json"}
        try:
            if client is not None:
                try:
                    response = client.post(
                        self.endpoint,
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=self.timeout,
                    )
                except TypeError:
                    response = client.post(
                        self.endpoint,
                        headers=headers,
                        files=files,
                        data=data,
                    )
            else:
                response = httpx.post(  # type: ignore[union-attr]
                    self.endpoint,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=self.timeout,
                )
            response.raise_for_status()
        except Exception as exc:
            raise VoiceUnavailable(
                f"no fue posible transcribir el audio con Whisper: {exc}"
            ) from exc

        try:
            payload = response.json()
        except Exception as exc:
            raise VoiceUnavailable("Whisper devolvio una respuesta que no es JSON") from exc
        if not isinstance(payload, Mapping):
            raise VoiceUnavailable("Whisper devolvio una respuesta inesperada")
        text = str(payload.get("text") or "").strip()
        if not text:
            raise VoiceUnavailable("Whisper no encontro una transcripcion en el audio")
        return text


__all__ = [
    "DEFAULT_WHISPER_MODEL",
    "GROQ_WHISPER_URL",
    "VoiceService",
    "VoiceUnavailable",
]
