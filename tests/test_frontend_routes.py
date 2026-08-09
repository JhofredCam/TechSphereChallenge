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
