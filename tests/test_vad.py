from __future__ import annotations

import pytest

from app.config import (
    DEFAULT_VOICE_SILENCE_TIMEOUT_MS,
    DEFAULT_VOICE_SPEECH_START_TIMEOUT_MS,
    DEFAULT_VOICE_VAD_RMS_THRESHOLD,
    Settings,
)
from app.services.vad import VadConfig, VadState, next_vad_state


def test_vad_defaults_are_public_and_configurable():
    settings = Settings.from_env(
        {
            "APP_DATA_DIR": ".pytest-tmp/vad-settings",
            "VOICE_SILENCE_TIMEOUT_MS": "2500",
            "VOICE_VAD_RMS_THRESHOLD": "0.04",
            "VOICE_SPEECH_START_TIMEOUT_MS": "12000",
        }
    )
    assert settings.voice_silence_timeout_ms == 2500
    assert settings.voice_vad_rms_threshold == 0.04
    assert settings.voice_speech_start_timeout_ms == 12000
    defaults = Settings()
    assert defaults.voice_silence_timeout_ms == DEFAULT_VOICE_SILENCE_TIMEOUT_MS
    assert defaults.voice_vad_rms_threshold == DEFAULT_VOICE_VAD_RMS_THRESHOLD
    assert defaults.voice_speech_start_timeout_ms == DEFAULT_VOICE_SPEECH_START_TIMEOUT_MS


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("VOICE_SILENCE_TIMEOUT_MS", "499"),
        ("VOICE_SILENCE_TIMEOUT_MS", "10001"),
        ("VOICE_VAD_RMS_THRESHOLD", "0.0009"),
        ("VOICE_VAD_RMS_THRESHOLD", "0.201"),
        ("VOICE_SPEECH_START_TIMEOUT_MS", "999"),
        ("VOICE_SPEECH_START_TIMEOUT_MS", "30001"),
    ],
)
def test_vad_configuration_bounds_are_rejected(name, value):
    with pytest.raises(ValueError, match=name):
        Settings.from_env({name: value})


def test_silence_only_finalizes_after_confirmed_text_and_timeout():
    config = VadConfig(silence_timeout_ms=2000, rms_threshold=0.025)
    state = next_vad_state(VadState(), rms=0.04, config=config, now_ms=0)
    assert state.has_speech is True
    state = next_vad_state(
        state,
        rms=0.0,
        config=config,
        now_ms=100,
        confirmed_text="dolor en la herida",
    )
    assert state.should_finalize is False
    state = next_vad_state(state, rms=0.0, config=config, now_ms=2099)
    assert state.should_finalize is False
    state = next_vad_state(state, rms=0.0, config=config, now_ms=2100)
    assert state.phase == "PROCESSING"
    assert state.should_finalize is True


def test_empty_silence_never_becomes_a_clinical_turn():
    config = VadConfig()
    state = next_vad_state(VadState(), rms=0.04, config=config, now_ms=0)
    state = next_vad_state(state, rms=0.0, config=config, now_ms=5000)
    assert state.should_finalize is False
