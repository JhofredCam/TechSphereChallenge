from __future__ import annotations

from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[1] / "app" / "web"


def test_call_surface_exposes_conversation_first_and_operational_rail():
    html = (WEB_DIR / "call.html").read_text(encoding="utf-8")
    assert 'id="conversation-panel"' in html
    assert 'id="turn-list" class="turn-list" role="log" aria-live="off"' in html
    assert 'id="call-rail"' in html
    assert 'aria-labelledby="rail-title"' in html
    assert "Estado de la llamada" in html
    assert "Fuentes consultadas" in html
    assert "Finalizar atención" in html
    assert 'id="patient-name"' not in html
    assert 'id="procedure"' not in html


def test_call_state_projection_and_safe_source_copy_are_explicit():
    javascript = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")
    assert "function renderCallState(state)" in javascript
    assert 'renderCallState("processing")' in javascript
    assert 'renderCallState("responding")' in javascript
    assert 'renderCallState("finished")' in javascript
    assert 'window.confirm("¿Quieres finalizar' in javascript
    assert "source.chunk_id" not in javascript
    assert "source.score" not in javascript
    assert "prefers-reduced-motion" in styles
    assert ".call-rail::before" in styles
