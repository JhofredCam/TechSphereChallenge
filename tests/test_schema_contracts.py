from __future__ import annotations

from app.schemas import DatasetTableReport, DatasetValidationReport, DocumentRecord, SearchResult


def test_schema_defaults_and_traceability_properties_are_stable():
    record = DocumentRecord.from_row(
        {
            "id": "doc-1",
            "filename": "guide.txt",
            "stored_path": "internal-only",
            "sha256": "a" * 64,
            "size_bytes": 4,
            "mime_type": "text/plain",
            "status": "custom",
            "error": None,
            "created_at": "2026-01-01",
            "processed_at": None,
        }
    )
    source = SearchResult(
        document_id="doc-1",
        filename="guide.txt",
        page_number=1,
        chunk_id="chunk-1",
        text="Contenido",
        score=1.0,
        citation="guide.txt (p. 1)",
        corpus_revision=2,
    )
    report = DatasetValidationReport(
        tables=(DatasetTableReport("fixture.xlsx", "result", ("id",), 1),)
    )

    assert record.status_value == "custom"
    assert record.rag_eligible is False
    assert record.available is False
    assert record.needs_ocr is False
    assert record.preview_available is False
    assert source.source == "guide.txt (p. 1)"
    assert report.valid is True
    assert report.row_counts == {"fixture.xlsx": 1}
