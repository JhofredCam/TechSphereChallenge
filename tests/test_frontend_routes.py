from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app


def test_demo_routes_are_directly_served_without_internal_paths(tmp_path):
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    application = create_app(settings=settings, database=database)
    try:
        with TestClient(application) as client:
            pages = {
                "/": "data-page=\"landing\"",
                "/patient": "data-page=\"patient-access\"",
                "/admin/access": "data-page=\"admin-access\"",
                "/admin": "data-page=\"admin\"",
                "/call": "data-page=\"call\"",
            }
            for path, marker in pages.items():
                response = client.get(path)
                assert response.status_code == 200
                assert marker in response.text
                assert "stored_path" not in response.text
    finally:
        database.close()


def test_landing_links_to_both_entries_and_call_has_no_registration_form(tmp_path):
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    application = create_app(settings=settings, database=database)
    try:
        with TestClient(application) as client:
            landing = client.get("/").text
            assert 'href="/patient"' in landing
            assert 'href="/admin/access"' in landing

            call = client.get("/call").text
            assert 'id="start-call"' in call
            assert 'id="patient-name"' not in call
            assert 'id="procedure"' not in call
            assert 'id="day-postop"' not in call
            assert 'id="call-form"' not in call
            assert 'src="/static/session.js"' in call
    finally:
        database.close()


def test_frontend_pages_and_assets_are_not_cached(tmp_path):
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    application = create_app(settings=settings, database=database)
    try:
        with TestClient(application) as client:
            for path in ("/call", "/static/app.js", "/static/voice-loop.js"):
                response = client.get(path)
                assert response.status_code == 200
                assert response.headers["cache-control"] == "no-store, max-age=0"
                assert response.headers["pragma"] == "no-cache"
            call = client.get("/call")
            assert "/static/app.js?v=20260809-voice-timeout" in call.text
            assert "/static/voice-loop.js?v=20260809-voice-timeout" in call.text
    finally:
        database.close()
