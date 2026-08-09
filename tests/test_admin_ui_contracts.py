import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app" / "web"


def read_web_file(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_admin_markup_keeps_semantic_inventory_and_closed_preview_contract():
    html = read_web_file("admin.html")

    assert '<table class="documents-table">' in html
    assert "<caption" in html
    assert '<thead>' in html
    assert '<th scope="col">' in html
    assert '<tbody id="document-rows">' in html
    assert 'id="preview-panel"' in html
    assert 'tabindex="-1"' in html
    assert 'aria-live="polite"' in html


def test_admin_layout_uses_stateful_grid_and_mobile_cards_without_horizontal_hack():
    css = read_web_file("styles.css")

    assert re.search(
        r"\.admin-workspace\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)",
        css,
    )
    assert re.search(
        r"\.admin-workspace\.preview-open\s*\{[^}]*grid-template-columns:",
        css,
    )
    assert "overflow-x: hidden" not in css
    assert "overflow-x: auto" not in css
    assert ".documents-table tr.document-row" in css
    assert ".documents-table td::before" in css
    assert ".document-content" in css
    assert "nth-child(4), .documents-table td:nth-child(4) { display: none; }" not in css


def test_admin_javascript_keeps_internal_identity_out_of_dom_and_renders_text_safely():
    javascript = read_web_file("app.js")
    admin_code = javascript.split("const TEXT_INPUT_TIMING", 1)[0]

    assert "innerHTML" not in admin_code
    assert "sha256" not in admin_code.lower()
    assert "document_id" not in admin_code.lower()
    assert "stored_path" not in admin_code.lower()
    assert "textContent = documentRecord.filename" in admin_code
    assert "textContent = documentRecord.id" not in admin_code
    assert admin_code.count("encodeURIComponent(documentRecord.id)") >= 3
    assert "documentRecord.id.slice" not in admin_code
    assert not re.search(r"(?:title|aria-label)\s*=.*documentRecord\.id", admin_code)
    assert "error.message" not in admin_code
    assert "textContent" in admin_code


def test_admin_copy_covers_processing_publication_and_client_facing_states():
    javascript = read_web_file("app.js")

    for phrase in (
        "Disponible",
        "Necesita revisión",
        "Procesando",
        "Error al procesar",
        "Disponible para el agente",
        "No disponible para el agente",
        "No publicable",
        "No encontramos texto utilizable. Se necesita OCR.",
        "No pudimos actualizar la lista. Inténtalo de nuevo.",
    ):
        assert phrase in javascript
