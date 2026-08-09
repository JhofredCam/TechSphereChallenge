from __future__ import annotations

from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[1] / "app" / "web"


def test_demo_session_contract_uses_versioned_session_storage_only():
    source = (WEB_DIR / "session.js").read_text(encoding="utf-8")
    assert 'techsphere.demo.session.v1' in source
    assert "sessionStorage" in source
    assert "localStorage" not in source
    assert "role: \"patient\"" in source
    assert "role: \"admin\"" in source
    assert "clear();" in source
    assert "password:" not in source.lower()


def test_access_validates_demo_password_without_persisting_or_sending_it():
    source = (WEB_DIR / "access.js").read_text(encoding="utf-8")
    session_source = (WEB_DIR / "session.js").read_text(encoding="utf-8")
    call_source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "DEMO_PASSWORD" in source
    assert "sessionApi.save(result.session)" in source
    assert "JSON.stringify(payload)" not in source
    assert "password:" not in session_source.lower()
    assert "password" not in call_source.lower()


def test_patient_and_admin_access_have_demo_disclaimer_and_no_real_auth_surface():
    for filename in ("patient-access.html", "admin-access.html"):
        html = (WEB_DIR / filename).read_text(encoding="utf-8")
        assert "Acceso de demostración" in html
        assert "No se guarda" in html
        assert "session.js" in html
        assert "JWT" not in html
