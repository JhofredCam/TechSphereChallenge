from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.config import Settings
from app.database import init_database
from app.dataset import validate_joins, validate_workbook
from app.schemas import DocumentStatus
from app.services.documents import DocumentService
from app.services.ingestion import (
    IngestionError,
    UnsupportedFileTypeError,
    chunk_pages,
    extract_document,
    extract_pages,
    guess_mime_type,
    iter_supported_files,
    normalize_for_search,
)


def test_recursive_text_extraction_supports_spaces_and_page_chunks(tmp_path):
    nested = tmp_path / "clinical corpus" / "post op"
    nested.mkdir(parents=True)
    source = nested / "guide final.md"
    source.write_text(
        "La colecistectomía requiere vigilancia.\n\n"
        "Consulte si aparece fiebre persistente.",
        encoding="utf-8",
    )

    assert list(iter_supported_files(tmp_path)) == [source]
    pages = extract_pages(source)
    chunks = chunk_pages(
        pages,
        document_id="document-hash",
        chunk_size=32,
        chunk_overlap=5,
    )

    assert pages[0].page_number == 1
    assert pages[0].needs_ocr is False
    assert len(chunks) >= 2
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert all(chunk.document_id == "document-hash" for chunk in chunks)
    assert all(chunk.start_char < chunk.end_char for chunk in chunks)
    assert chunks[0].id == chunk_pages(
        pages,
        document_id="document-hash",
        chunk_size=32,
        chunk_overlap=5,
    )[0].id
    assert "colecistectomia" in normalize_for_search("COLECISTECTOMÍA")


def test_empty_text_source_is_marked_needs_ocr(tmp_path):
    source = tmp_path / "empty.txt"
    source.write_text("   \n", encoding="utf-8")

    result = extract_document(source)

    assert result.status is DocumentStatus.NEEDS_OCR
    assert result.pages[0].needs_ocr is True
    assert result.pages[0].text.strip() == ""


def test_xlsx_helpers_validate_result_json_counts_and_joins(tmp_path):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "result"
    worksheet.append(["paciente_id", "comorbilidades"])
    worksheet.append(["pac-1", "[]"])
    source = tmp_path / "table.xlsx"
    workbook.save(source)

    report = validate_workbook(
        source,
        expected_headers=("paciente_id", "comorbilidades"),
        expected_rows=1,
        json_fields=("comorbilidades",),
    )

    assert report.valid is True
    assert validate_joins(
        [{"paciente_id": "pac-1"}],
        [{"paciente_id": "pac-1"}],
        [{"trayectoria_id": "t-1", "paciente_id": "pac-1"}],
        [{
            "caso_id": "caso_t-1",
            "paciente_id": "pac-1",
            "capa": "capa1_limpia",
        }],
    ) == ()


def test_pdf_pages_and_zero_text_are_explicit_when_pymupdf_is_available(tmp_path):
    fitz = pytest.importorskip("fitz")
    text_pdf = tmp_path / "with text.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Texto clínico de prueba")
    pdf.save(text_pdf)
    pdf.close()

    extracted = extract_document(text_pdf)
    assert extracted.status is DocumentStatus.AVAILABLE
    assert extracted.pages[0].page_number == 1
    assert "Texto clínico" in extracted.pages[0].text

    blank_pdf = tmp_path / "scanned.pdf"
    pdf = fitz.open()
    pdf.new_page()
    pdf.save(blank_pdf)
    pdf.close()

    scanned = extract_document(blank_pdf)
    assert scanned.status is DocumentStatus.NEEDS_OCR
    assert scanned.pages[0].needs_ocr is True


def test_document_storage_names_are_windows_safe_and_hash_idempotent(tmp_path):
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)
    documents = DocumentService(database, settings)
    long_name = ("a" * 320) + ".txt"

    first = documents.upload(b"same clinical content", "CON:" + long_name)
    duplicate = documents.upload(b"same clinical content", "renamed with spaces.txt")

    assert duplicate.id == first.id
    assert first.filename != "CON:" + long_name
    assert first.filename.casefold().split(".", 1)[0] != "con"
    assert all(character not in first.filename for character in '<>:"/\\|?*')
    assert not first.filename.endswith((".", " "))
    assert len(str(Path(first.stored_path))) <= 240
    assert Path(first.stored_path).is_file()


def test_ingestion_rejects_corrupt_pdfs_unsupported_types_and_missing_roots(tmp_path):
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"not a pdf")
    unsupported = tmp_path / "notes.csv"
    unsupported.write_text("content", encoding="utf-8")

    with pytest.raises(IngestionError, match="could not extract PDF"):
        extract_document(corrupt)
    with pytest.raises(UnsupportedFileTypeError):
        extract_pages(unsupported)
    with pytest.raises(FileNotFoundError):
        list(iter_supported_files(tmp_path / "missing corpus"))
    assert guess_mime_type("notes.unknown") == "application/octet-stream"


def test_chunking_rejects_invalid_overlap_and_size():
    with pytest.raises(ValueError, match="chunk_size"):
        from app.schemas import ExtractedPage

        chunk_pages([ExtractedPage(1, "text")], chunk_size=0)
    with pytest.raises(ValueError, match="chunk_overlap"):
        from app.schemas import ExtractedPage

        chunk_pages([ExtractedPage(1, "text")], chunk_size=2, chunk_overlap=2)


def test_document_upload_accepts_paths_and_binary_streams_but_requires_names(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    database = init_database(settings)
    documents = DocumentService(database, settings)
    source = tmp_path / "nested" / "guide.txt"
    source.parent.mkdir()
    source.write_text("Contenido desde una ruta.", encoding="utf-8")

    from_path = documents.upload(source)
    from_stream = documents.upload(BytesIO(b"Contenido desde un stream."), "stream.txt")

    assert from_path.filename == "guide.txt"
    assert from_stream.filename == "stream.txt"
    with pytest.raises(ValueError, match="filename is required"):
        documents.upload(b"bytes without a name")
    with pytest.raises(TypeError, match="source must be"):
        documents.upload(object())  # type: ignore[arg-type]


def test_document_upload_handles_text_readers_and_refuses_cleanup_outside_storage(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    database = init_database(settings)
    documents = DocumentService(database, settings)

    class TextReader:
        filename = "reader.txt"

        def read(self):
            return "Contenido textual del lector."

    class InvalidReader:
        def read(self):
            return 123

    class NoNameReader:
        def read(self):
            return b"missing filename"

    reader_record = documents.upload(TextReader())
    assert reader_record.filename == "reader.txt"
    with pytest.raises(TypeError, match="must return bytes"):
        documents.upload(InvalidReader(), "invalid.txt")
    with pytest.raises(ValueError, match="filename is required"):
        documents.upload(NoNameReader())

    uploaded = documents.upload(b"Contenido que no debe borrar fuera", "outside.txt")
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"keep me")
    database.execute(
        "UPDATE documents SET stored_path = ? WHERE id = ?",
        (str(outside), uploaded.id),
    )

    assert documents.delete(uploaded.id) is True
    assert outside.exists()
    audit = database.execute(
        "SELECT action FROM audit WHERE entity_id = ? ORDER BY id DESC LIMIT 1",
        (uploaded.id,),
    ).fetchone()
    assert audit["action"] == "delete_storage_error"
