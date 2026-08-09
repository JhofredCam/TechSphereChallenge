"""Pure RMS VAD state transition used by deterministic tests and the browser loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class VadConfig:
    silence_timeout_ms: int = 2_000
    rms_threshold: float = 0.025
    speech_start_timeout_ms: int = 10_000


@dataclass(frozen=True, slots=True)
class VadState:
    has_speech: bool = False
    silence_started_at: float | None = None
    confirmed_text: str = ""
    phase: str = "LISTENING"
    should_finalize: bool = False


def next_vad_state(
    previous: VadState | Mapping[str, object],
    *,
    rms: float,
    config: VadConfig,
    now_ms: float,
    confirmed_text: str | None = None,
) -> VadState:
    """Advance VAD without inspecting or persisting the audio samples."""

    if config.silence_timeout_ms < 500 or not 0.001 <= config.rms_threshold <= 0.2:
        raise ValueError("invalid VAD configuration")
    if isinstance(previous, VadState):
        has_speech = previous.has_speech
        silence_started = previous.silence_started_at
        previous_text = previous.confirmed_text
    else:
        has_speech = bool(previous.get("hasSpeech", previous.get("has_speech", False)))
        silence_started = previous.get("silenceStartedAt", previous.get("silence_started_at"))
        previous_text = str(previous.get("confirmedText", previous.get("confirmed_text", "")))
    text = previous_text if confirmed_text is None else str(confirmed_text)
    speaking = float(rms) >= config.rms_threshold
    if speaking:
        has_speech = True
        silence_started = None
    elif has_speech and silence_started is None:
        silence_started = now_ms
    silence_ms = 0.0 if silence_started is None else max(0.0, now_ms - float(silence_started))
    should_finalize = bool(has_speech and text.strip() and silence_ms >= config.silence_timeout_ms)
    return VadState(
        has_speech=has_speech,
        silence_started_at=silence_started,
        confirmed_text=text,
        phase="PROCESSING" if should_finalize else "LISTENING",
        should_finalize=should_finalize,
    )


__all__ = ["VadConfig", "VadState", "next_vad_state"]
