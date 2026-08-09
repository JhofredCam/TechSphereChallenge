from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.services.documents import DocumentService


@pytest.fixture
def source_context(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    documents = DocumentService(database, settings)
    return TestClient(create_app(settings=settings, database=database)), database, documents


def test_source_endpoint_serves_literal_text_with_safe_headers(source_context):
    client, database, documents = source_context
    content = b"<script>alert('not executable')</script>\n# Literal markdown"
    record = documents.upload(content, "guide.md")
    revision = database.get_corpus_revision()
    listed = client.get("/api/admin/documents").json()["documents"][0]

    assert listed["source_format"] == "md"
    assert listed["source_media_type"] == "text/plain"
    assert listed["original_preview_available"] is True
    assert "stored_path" not in listed

    response = client.get(f"/api/admin/documents/{record.id}/source")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.headers["content-disposition"].startswith("inline;")
    assert "guide.md" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert database.get_corpus_revision() == revision


def test_source_endpoint_serves_original_pdf_bytes_and_canonical_mime(source_context):
    client, _, documents = source_context
    fitz = pytest.importorskip("fitz")
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Fuente original")
    content = pdf.tobytes()
    pdf.close()
    record = documents.upload(content, "guia.pdf")

    response = client.get(f"/api/admin/documents/{record.id}/source")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"


def test_source_states_do_not_leak_content_or_paths(source_context):
    client, _, documents = source_context
    processing = documents.upload(b"processing", "processing.txt", process=False)
    error = documents.upload(b"not really a csv", "broken.csv", process=False)
    documents.process(error.id)

    processing_response = client.get(f"/api/admin/documents/{processing.id}/source")
    assert processing_response.status_code == 409
    assert processing_response.json()["detail"] == {
        "error_code": "document_processing",
        "message": "La fuente aun se esta procesando.",
    }

    error_response = client.get(f"/api/admin/documents/{error.id}/source")
    assert error_response.status_code == 409
    assert error_response.json()["detail"]["error_code"] == "source_unavailable"
    assert "stored_path" not in error_response.text

    assert client.get("/api/admin/documents/missing/source").status_code == 404
    assert client.get("/api/admin/documents/missing/source").json()["detail"]["error_code"] == (
        "document_not_found"
    )


def test_source_rejects_missing_or_replaced_original_safely(source_context):
    client, _, documents = source_context
    record = documents.upload(b"contenido original", "source.txt")
    stored_path = Path(record.stored_path)
    stored_path.write_bytes(b"contenido que no coincide")

    response = client.get(f"/api/admin/documents/{record.id}/source")

    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "source_unavailable"
    assert "source.txt" not in response.text

    stored_path.unlink()
    missing = client.get(f"/api/admin/documents/{record.id}/source")
    assert missing.status_code == 409
    assert missing.json()["detail"]["error_code"] == "source_unavailable"


def test_admin_preview_surface_distinguishes_original_and_extracted_content():
    html = Path("app/web/admin.html").read_text(encoding="utf-8")
    javascript = Path("app/web/app.js").read_text(encoding="utf-8")
    styles = Path("app/web/styles.css").read_text(encoding="utf-8")

    assert '<dialog class="panel preview-panel"' in html
    assert 'role="tab"' in html
    assert 'id="preview-source-frame"' in html
    assert 'sandbox="allow-same-origin"' in html
    assert 'id="preview-source-text"' in html
    assert "/api/admin/documents/${encodeURIComponent(documentRecord.id)}/source" in javascript
    assert "sourceText.textContent" in javascript
    assert "dialog.preview-panel::backdrop" in styles
