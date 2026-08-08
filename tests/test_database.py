from __future__ import annotations

import sqlite3
import threading
import time

import pytest

from app.config import Settings
from app.database import init_database
from app.schemas import DocumentStatus


def test_init_database_configures_wal_foreign_keys_fts_and_meta(tmp_path):
    settings = Settings(data_dir=tmp_path)
    database = init_database(settings)

    assert database.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert database.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert {
        "documents",
        "pages",
        "chunks",
        "chunks_fts",
        "calls",
        "turns",
        "sources",
        "audit",
        "meta",
    } <= database.table_names()
    assert database.get_corpus_revision() == 0
    assert settings.db_path.exists()
    assert settings.documents_dir.exists()


def test_document_rows_and_revision_use_bound_values(tmp_path):
    database = init_database(Settings(data_dir=tmp_path))
    filename = "guide'); DROP TABLE documents;--.txt"
    document = database.create_document(
        document_id="doc-1",
        sha256="a" * 64,
        filename=filename,
        stored_path=str(tmp_path / filename),
        mime_type="text/plain",
        size_bytes=12,
        status=DocumentStatus.PROCESSING,
    )

    assert document.filename == filename
    assert database.get_document("doc-1") is not None
    assert database.get_document_by_hash("a" * 64).id == "doc-1"
    assert database.increment_corpus_revision() == 1
    assert database.get_corpus_revision() == 1
    assert "documents" in database.table_names()


def test_foreign_keys_reject_orphan_pages(tmp_path):
    database = init_database(Settings(data_dir=tmp_path))

    with pytest.raises(sqlite3.IntegrityError):
        database.insert_page(
            page_id="page-1",
            document_id="missing",
            page_number=1,
            text="orphan",
            needs_ocr=False,
        )


def test_transactions_are_serialized_and_nested_transactions_are_reentrant(tmp_path):
    database = init_database(Settings(data_dir=tmp_path))
    first_started = threading.Event()
    second_attempted = threading.Event()
    order: list[str] = []

    def first_writer() -> None:
        with database.transaction() as connection:
            order.append("first-start")
            first_started.set()
            assert second_attempted.wait(timeout=2)
            time.sleep(0.05)
            connection.execute("INSERT INTO meta(key, value) VALUES (?, ?)", ("first", "1"))
            order.append("first-end")

    def second_writer() -> None:
        assert first_started.wait(timeout=2)
        second_attempted.set()
        with database.transaction() as connection:
            order.append("second-start")
            connection.execute("INSERT INTO meta(key, value) VALUES (?, ?)", ("second", "1"))
            order.append("second-end")

    first = threading.Thread(target=first_writer)
    second = threading.Thread(target=second_writer)
    first.start()
    second.start()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert order == ["first-start", "first-end", "second-start", "second-end"]
    with database.transaction():
        with database.transaction():
            assert database.get_meta("first") == "1"
            assert database.get_meta("second") == "1"
