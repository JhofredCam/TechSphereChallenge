from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXPLORER_FILES = (
    DOCS / "architecture_explorer.html",
    DOCS / "architecture_explorer.css",
    DOCS / "architecture_explorer.js",
    DOCS / "architecture_explorer.data.js",
)


def test_offline_explorer_has_four_local_artifacts_and_semantic_landmarks():
    html = (DOCS / "architecture_explorer.html").read_text(encoding="utf-8")

    assert all(path.is_file() for path in EXPLORER_FILES)
    for marker in (
        '<html lang="es">',
        '<header',
        '<nav',
        '<main id="main-content"',
        '<aside',
        '<footer',
        'href="#main-content">Saltar al contenido',
        'id="flow"',
        'id="views"',
        'id="catalog"',
        'id="evidence"',
        'id="glossary"',
    ):
        assert marker in html
    assert 'architecture_explorer.css' in html
    assert 'architecture_explorer.data.js' in html
    assert 'architecture_explorer.js' in html
    assert 'microfono' not in html.lower()


def test_catalog_covers_required_prefixes_ids_views_stages_and_statuses():
    source = (DOCS / "architecture_explorer.data.js").read_text(encoding="utf-8")
    ids = set(re.findall(r'"([A-Z]+-[A-Z0-9_-]+-[0-9]{3})"', source))

    assert {"ACT", "UI", "API", "STG", "MOD", "EXT", "DATA", "STATE", "RULE", "MET", "TRZ", "TEST", "GATE"} <= {
        item.split("-", 1)[0] for item in ids
    }
    assert {
        "ACT-PATIENT-001", "ACT-ADMIN-001", "ACT-BROWSER-001",
        "UI-ADMIN-001", "UI-CALL-001", "UI-TEXT-FALLBACK-001",
        "API-ADMIN-LIST-001", "API-ADMIN-PREVIEW-001", "API-ADMIN-SOURCE-001",
        "API-ADMIN-TOGGLE-001", "API-ADMIN-DELETE-001", "API-CALL-TURN-001",
        "STG-BOOT-001", "STG-ADMIN-001", "STG-CALL-001", "STG-VOICE-001",
        "STG-TRIAGE-001", "STG-RAG-001", "STG-AGENT-001", "STG-TTS-001",
        "STG-OBS-001", "STG-CLOSE-001", "MOD-RAG-001", "MOD-AGENT-001",
        "MOD-TRIAGE-001", "MOD-DOCUMENT-001", "MOD-INGEST-001", "MOD-CALL-001",
        "MOD-METRICS-001", "STATE-DOC-AVAILABLE-001", "STATE-DOC-OCR-001",
        "STATE-VOICE-TIMEOUT-001", "RULE-RED-001", "RULE-YELLOW-001",
        "RULE-UNKNOWN-001", "RULE-RAG-ELIGIBLE-001", "RULE-SECURITY-001",
        "MET-VOICE-LATENCY-001", "MET-TOKENS-001", "MET-MODEL-CALLS-001",
        "MET-RAG-QUERIES-001", "MET-COST-001", "GATE-G1-001", "GATE-G2-001",
        "GATE-G3-001", "GATE-G4-001", "GATE-G5-001",
    } <= ids
    for value in ("D1", "D2", "D3", "D4", "D5", "D6", "IMPLEMENTED", "TESTED", "MANUAL_PENDING", "PROPOSED", "OUT_OF_SCOPE"):
        assert value in source


def test_each_catalog_entity_contract_is_generated_with_provenance():
    source = (DOCS / "architecture_explorer.data.js").read_text(encoding="utf-8")

    for field in (
        "entity_id", "kind", "title", "summary", "description", "status",
        "status_scope", "views", "stages", "inputs", "outputs", "invariants",
        "code_refs", "test_refs", "source_refs", "related_ids", "evidence",
        "divergences", "tags", "generated_at", "source_spec_version", "commit",
    ):
        assert field in source
    assert "source_refs" in source
    assert "source_spec_version" in source
    assert "working tree/no commit" in source


def test_explorer_is_offline_and_does_not_expose_runtime_or_execute_catalog_content():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in EXPLORER_FILES)

    assert "fetch(" not in combined
    assert "WebSocket" not in combined
    assert "innerHTML" not in combined
    assert "eval(" not in combined
    assert "new Function" not in combined
    assert "stored_path" not in combined
    assert "data/" not in combined
    assert "events.jsonl" not in combined
    assert ".sqlite3" not in combined
    assert "http://" not in combined
    assert "https://" not in combined
    assert "<script>" not in combined
    assert "onclick=" not in combined


def test_explorer_has_required_navigation_and_accessible_detail_contracts():
    html = (DOCS / "architecture_explorer.html").read_text(encoding="utf-8")
    javascript = (DOCS / "architecture_explorer.js").read_text(encoding="utf-8")
    css = (DOCS / "architecture_explorer.css").read_text(encoding="utf-8")

    assert 'id="catalog-search"' in html
    assert 'aria-live="polite"' in html
    assert 'id="entity-detail"' in html
    assert 'setAttribute("aria-controls", "entity-detail")' in javascript
    assert 'aria-expanded' in javascript
    assert 'hashchange' in javascript
    assert 'prefers-reduced-motion' in css
    assert '@media print' in css
    assert 'max-width: 420px' in css
