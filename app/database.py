"""SQLite persistence for documents, calls, and grounded source records."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterator, Mapping

from .config import Settings
from .schemas import DocumentRecord, DocumentStatus


def utc_now() -> str:
    """Return a sortable, timezone-aware timestamp."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA_VERSION = 3


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        sha256 TEXT NOT NULL UNIQUE,
        filename TEXT NOT NULL,
        stored_path TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
        status TEXT NOT NULL CHECK (
            status IN ('processing', 'available', 'needs_ocr', 'error')
        ),
        enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
        error TEXT,
        created_at TEXT NOT NULL,
        processed_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pages (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        page_number INTEGER NOT NULL CHECK (page_number > 0),
        text TEXT NOT NULL,
        needs_ocr INTEGER NOT NULL DEFAULT 0 CHECK (needs_ocr IN (0, 1)),
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
        UNIQUE (document_id, page_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        page_id TEXT NOT NULL,
        page_number INTEGER NOT NULL CHECK (page_number > 0),
        chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
        text TEXT NOT NULL,
        start_char INTEGER NOT NULL CHECK (start_char >= 0),
        end_char INTEGER NOT NULL CHECK (end_char >= start_char),
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
        FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE,
        UNIQUE (document_id, page_number, chunk_index)
    )
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
        chunk_id UNINDEXED,
        document_id UNINDEXED,
        page_number UNINDEXED,
        text,
        tokenize = 'unicode61 remove_diacritics 2'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calls (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        procedure TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        started_at TEXT NOT NULL,
        ended_at TEXT,
        summary_json TEXT,
        triage_level TEXT,
        alert INTEGER NOT NULL DEFAULT 0 CHECK (alert IN (0, 1)),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS turns (
        id TEXT PRIMARY KEY,
        call_id TEXT NOT NULL,
        turn_index INTEGER NOT NULL CHECK (turn_index >= 0),
        speaker TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        latency_ms REAL,
        input_tokens INTEGER,
        output_tokens INTEGER,
        model_calls INTEGER NOT NULL DEFAULT 0,
        rag_queries INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (call_id) REFERENCES calls(id) ON DELETE CASCADE,
        UNIQUE (call_id, turn_index)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS listening_attempts (
        listen_id TEXT PRIMARY KEY,
        call_id TEXT NOT NULL,
        client_turn_id TEXT,
        status TEXT NOT NULL CHECK (
            status IN (
                'LISTENING', 'PARTIAL', 'FINAL_RECEIVED', 'PROCESSING',
                'NO_RESPONSE', 'LISTEN_TIMEOUT', 'RECOGNITION_ERROR',
                'RETRY_REQUIRED', 'COMPLETED'
            )
        ),
        configured_timeout_ms INTEGER NOT NULL CHECK (
            configured_timeout_ms BETWEEN 1000 AND 300000
        ),
        elapsed_ms REAL CHECK (elapsed_ms IS NULL OR elapsed_ms >= 0),
        locale TEXT NOT NULL,
        implementation TEXT NOT NULL,
        error_code TEXT,
        patient_turn_id TEXT,
        agent_turn_id TEXT,
        response_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (call_id) REFERENCES calls(id) ON DELETE CASCADE,
        FOREIGN KEY (patient_turn_id) REFERENCES turns(id) ON DELETE SET NULL,
        FOREIGN KEY (agent_turn_id) REFERENCES turns(id) ON DELETE SET NULL,
        UNIQUE (call_id, client_turn_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        turn_id TEXT,
        document_id TEXT,
        chunk_id TEXT,
        page_number INTEGER,
        score REAL,
        citation TEXT NOT NULL,
        corpus_revision INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        document_filename_snapshot TEXT,
        document_sha256_snapshot TEXT,
        chunk_index_snapshot INTEGER,
        FOREIGN KEY (turn_id) REFERENCES turns(id) ON DELETE CASCADE,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL,
        FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        action TEXT NOT NULL,
        details_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)",
    "CREATE INDEX IF NOT EXISTS idx_pages_document ON pages(document_id, page_number)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id, page_number)",
    "CREATE INDEX IF NOT EXISTS idx_turns_call ON turns(call_id, turn_index)",
    "CREATE INDEX IF NOT EXISTS idx_listening_attempts_call "
    "ON listening_attempts(call_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_listening_attempts_client "
    "ON listening_attempts(client_turn_id)",
    "CREATE INDEX IF NOT EXISTS idx_sources_turn ON sources(turn_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit(entity_type, entity_id)",
)


_DOCUMENT_SELECT = """
    SELECT
        documents.*,
        (
            SELECT COUNT(*)
            FROM pages AS document_pages
            WHERE document_pages.document_id = documents.id
        ) AS page_count,
        (
            SELECT COUNT(*)
            FROM chunks AS document_chunks
            WHERE document_chunks.document_id = documents.id
        ) AS chunk_count
    FROM documents
"""


class Database:
    """A small thread-local-friendly wrapper around a configured SQLite database.

    The wrapper keeps one connection so callers can use a transaction for a document
    replacement and its FTS rows.  All values supplied by callers are bound parameters;
    schema identifiers are fixed constants in this module.
    """

    def __init__(self, path: str | Path, *, initialize: bool = True) -> None:
        if isinstance(path, Settings):
            path = path.db_path
        self.path = Path(path)
        self._sqlite_path = ":memory:" if str(path) == ":memory:" else str(self.path)
        if self._sqlite_path != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            self._sqlite_path,
            timeout=5.0,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.execute("PRAGMA journal_mode = WAL")
        if initialize:
            self.initialize()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def initialize(self) -> None:
        """Create or migrate the schema before the application can serve requests."""

        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                for statement in SCHEMA_STATEMENTS:
                    self._connection.execute(statement)

                document_columns = self._column_names("documents")
                if "enabled" not in document_columns:
                    self._connection.execute(
                        "ALTER TABLE documents ADD COLUMN enabled INTEGER NOT NULL "
                        "DEFAULT 0 CHECK (enabled IN (0, 1))"
                    )
                    # Preserve the active baseline corpus, but never publish a
                    # document that was processing, awaiting OCR, or in error.
                    self._connection.execute(
                        "UPDATE documents SET enabled = CASE "
                        "WHEN status = 'available' THEN 1 ELSE 0 END"
                    )

                source_columns = self._column_names("sources")
                snapshot_columns = {
                    "document_filename_snapshot": "TEXT",
                    "document_sha256_snapshot": "TEXT",
                    "chunk_index_snapshot": "INTEGER",
                }
                for column, definition in snapshot_columns.items():
                    if column not in source_columns:
                        self._connection.execute(
                            f"ALTER TABLE sources ADD COLUMN {column} {definition}"
                        )

                # Backfill only while the referenced rows still exist.  COALESCE
                # keeps an existing snapshot immutable on later initializations.
                self._connection.execute(
                    """
                    UPDATE sources
                    SET document_filename_snapshot = COALESCE(
                            document_filename_snapshot,
                            (
                                SELECT filename
                                FROM documents
                                WHERE documents.id = sources.document_id
                            )
                        ),
                        document_sha256_snapshot = COALESCE(
                            document_sha256_snapshot,
                            (SELECT sha256 FROM documents WHERE documents.id = sources.document_id)
                        ),
                        chunk_index_snapshot = COALESCE(
                            chunk_index_snapshot,
                            (
                                SELECT chunk_index
                                FROM chunks
                                WHERE chunks.id = sources.chunk_id
                            )
                        )
                    WHERE document_id IS NOT NULL
                    """
                )
                self._connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_documents_rag_eligibility "
                    "ON documents(status, enabled)"
                )
                self._connection.execute(
                    "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                    ("corpus_revision", "0"),
                )
                self._connection.execute(
                    "INSERT INTO meta(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    ("schema_version", str(SCHEMA_VERSION)),
                )
                self._connection.commit()
            except sqlite3.OperationalError as exc:
                if self._connection.in_transaction:
                    self._connection.rollback()
                if "fts5" in str(exc).lower() or "no such module" in str(exc).lower():
                    raise RuntimeError("SQLite was built without FTS5 support") from exc
                raise
            except BaseException:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def _column_names(self, table_name: str) -> set[str]:
        rows = self._connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row["name"]) for row in rows}

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a block atomically, while allowing an existing transaction.

        The connection is shared by local request handlers, so the lock must cover the
        whole transaction rather than only the ``BEGIN`` statement.  ``RLock`` keeps
        nested service calls on the same thread valid.
        """

        with self._lock:
            started = not self._connection.in_transaction
            if started:
                self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except BaseException:
                if started:
                    self._connection.rollback()
                raise
            else:
                if started:
                    self._connection.commit()

    def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._connection.execute(sql, parameters)

    def executemany(
        self,
        sql: str,
        parameters: list[tuple[Any, ...]] | tuple[tuple[Any, ...], ...],
    ) -> sqlite3.Cursor:
        with self._lock:
            return self._connection.executemany(sql, parameters)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM meta WHERE key = ?",
                (key,),
            ).fetchone()
            return default if row is None else str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO meta(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_corpus_revision(self) -> int:
        with self._lock:
            value = self.get_meta("corpus_revision", "0")
            try:
                return int(value or 0)
            except ValueError as exc:
                raise RuntimeError("corpus_revision metadata is not an integer") from exc

    def get_listening_attempt(self, listen_id: str) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                "SELECT * FROM listening_attempts WHERE listen_id = ?",
                (listen_id,),
            ).fetchone()

    def get_listening_attempt_for_client(
        self,
        call_id: str,
        client_turn_id: str,
    ) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                "SELECT * FROM listening_attempts "
                "WHERE call_id = ? AND client_turn_id = ?",
                (call_id, client_turn_id),
            ).fetchone()

    def get_listening_attempt_by_client(self, client_turn_id: str) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                "SELECT * FROM listening_attempts WHERE client_turn_id = ?",
                (client_turn_id,),
            ).fetchone()

    def get_listening_attempt_for_turn(self, turn_id: str) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                "SELECT * FROM listening_attempts "
                "WHERE patient_turn_id = ? OR agent_turn_id = ? "
                "ORDER BY updated_at DESC LIMIT 1",
                (turn_id, turn_id),
            ).fetchone()

    def increment_corpus_revision(
        self,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        """Increment and return the revision inside or outside a caller transaction."""

        with self._lock:
            conn = connection or self._connection
            started = connection is None and not conn.in_transaction
            if started:
                conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                    ("corpus_revision", "0"),
                )
                conn.execute(
                    "UPDATE meta SET value = CAST(value AS INTEGER) + 1 WHERE key = ?",
                    ("corpus_revision",),
                )
                row = conn.execute(
                    "SELECT value FROM meta WHERE key = ?",
                    ("corpus_revision",),
                ).fetchone()
                revision = int(row["value"])
                if started:
                    conn.commit()
                return revision
            except BaseException:
                if started:
                    conn.rollback()
                raise

    def create_document(
        self,
        *,
        document_id: str,
        sha256: str,
        filename: str,
        stored_path: str,
        mime_type: str,
        size_bytes: int,
        status: DocumentStatus | str = DocumentStatus.PROCESSING,
        created_at: str | None = None,
    ) -> DocumentRecord:
        with self._lock:
            timestamp = created_at or utc_now()
            raw_status = status.value if isinstance(status, DocumentStatus) else str(status)
            self._connection.execute(
                """
                INSERT INTO documents(
                    id, sha256, filename, stored_path, mime_type, size_bytes,
                    status, enabled, error, created_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL)
                """,
                (
                    document_id,
                    sha256,
                    filename,
                    stored_path,
                    mime_type,
                    size_bytes,
                    raw_status,
                    int(raw_status == DocumentStatus.AVAILABLE.value),
                    timestamp,
                ),
            )
            record = self.get_document(document_id)
            if record is None:
                raise RuntimeError("document insert did not produce a row")
            return record

    def get_document(self, document_id: str) -> DocumentRecord | None:
        with self._lock:
            row = self._connection.execute(
                _DOCUMENT_SELECT + " WHERE documents.id = ?",
                (document_id,),
            ).fetchone()
            return None if row is None else DocumentRecord.from_row(row)

    def get_document_by_hash(self, sha256: str) -> DocumentRecord | None:
        with self._lock:
            row = self._connection.execute(
                _DOCUMENT_SELECT + " WHERE documents.sha256 = ?",
                (sha256,),
            ).fetchone()
            return None if row is None else DocumentRecord.from_row(row)

    def list_documents(self, status: DocumentStatus | str | None = None) -> list[DocumentRecord]:
        with self._lock:
            if status is None:
                rows = self._connection.execute(
                    _DOCUMENT_SELECT + " ORDER BY documents.created_at DESC, documents.id DESC"
                ).fetchall()
            else:
                raw_status = status.value if isinstance(status, DocumentStatus) else str(status)
                rows = self._connection.execute(
                    _DOCUMENT_SELECT + " WHERE documents.status = ? "
                    "ORDER BY documents.created_at DESC, documents.id DESC",
                    (raw_status,),
                ).fetchall()
            return [DocumentRecord.from_row(row) for row in rows]

    def update_document_status(
        self,
        document_id: str,
        status: DocumentStatus | str,
        *,
        error: str | None = None,
        processed_at: str | None = None,
        enabled: bool | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        with self._lock:
            conn = connection or self._connection
            raw_status = status.value if isinstance(status, DocumentStatus) else str(status)
            if enabled is None:
                if raw_status == DocumentStatus.AVAILABLE.value:
                    conn.execute(
                        "UPDATE documents SET status = ?, error = ?, processed_at = ? "
                        "WHERE id = ?",
                        (raw_status, error, processed_at, document_id),
                    )
                else:
                    conn.execute(
                        "UPDATE documents SET status = ?, enabled = 0, error = ?, "
                        "processed_at = ? WHERE id = ?",
                        (raw_status, error, processed_at, document_id),
                    )
            else:
                conn.execute(
                    "UPDATE documents SET status = ?, enabled = ?, error = ?, "
                    "processed_at = ? WHERE id = ?",
                    (raw_status, int(enabled), error, processed_at, document_id),
                )

    def set_document_enabled(
        self,
        document_id: str,
        enabled: bool,
    ) -> tuple[DocumentRecord, bool, int]:
        """Publish or unpublish an available document without touching its index."""

        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean")
        with self._lock:
            with self.transaction() as connection:
                row = connection.execute(
                    "SELECT status, enabled FROM documents WHERE id = ?",
                    (document_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(document_id)
                if str(row["status"]) != DocumentStatus.AVAILABLE.value:
                    raise ValueError("document_not_searchable")
                current = bool(int(row["enabled"] or 0))
                if current == enabled:
                    revision = self.get_corpus_revision()
                    changed = False
                else:
                    connection.execute(
                        "UPDATE documents SET enabled = ? WHERE id = ?",
                        (int(enabled), document_id),
                    )
                    revision = self.increment_corpus_revision(connection)
                    self.record_audit(
                        entity_type="document",
                        entity_id=document_id,
                        action="enable" if enabled else "disable",
                        details={
                            "enabled": enabled,
                            "corpus_revision": revision,
                        },
                        connection=connection,
                    )
                    changed = True
            record = self.get_document(document_id)
            if record is None:
                raise RuntimeError("document disappeared after publication update")
            return record, changed, revision

    def get_document_page(self, document_id: str, page_number: int) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                "SELECT id, document_id, page_number, text, needs_ocr "
                "FROM pages WHERE document_id = ? AND page_number = ?",
                (document_id, page_number),
            ).fetchone()

    def insert_page(
        self,
        *,
        page_id: str,
        document_id: str,
        page_number: int,
        text: str,
        needs_ocr: bool,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        with self._lock:
            conn = connection or self._connection
            conn.execute(
                """
                INSERT INTO pages(id, document_id, page_number, text, needs_ocr)
                VALUES (?, ?, ?, ?, ?)
                """,
                (page_id, document_id, page_number, text, int(needs_ocr)),
            )

    def insert_chunk(
        self,
        *,
        chunk_id: str,
        document_id: str,
        page_id: str,
        page_number: int,
        chunk_index: int,
        text: str,
        start_char: int,
        end_char: int,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        with self._lock:
            conn = connection or self._connection
            conn.execute(
                """
                INSERT INTO chunks(
                    id, document_id, page_id, page_number, chunk_index,
                    text, start_char, end_char
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    document_id,
                    page_id,
                    page_number,
                    chunk_index,
                    text,
                    start_char,
                    end_char,
                ),
            )
            conn.execute(
                """
                INSERT INTO chunks_fts(chunk_id, document_id, page_number, text)
                VALUES (?, ?, ?, ?)
                """,
                (chunk_id, document_id, page_number, text),
            )

    def clear_document_content(
        self,
        document_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        with self._lock:
            conn = connection or self._connection
            conn.execute("DELETE FROM chunks_fts WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM pages WHERE document_id = ?", (document_id,))

    def record_audit(
        self,
        *,
        entity_type: str,
        entity_id: str | None,
        action: str,
        details: Mapping[str, Any] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        with self._lock:
            conn = connection or self._connection
            details_json = json.dumps(details or {}, ensure_ascii=False, sort_keys=True)
            conn.execute(
                """
                INSERT INTO audit(entity_type, entity_id, action, details_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (entity_type, entity_id, action, details_json, utc_now()),
            )

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all searchable content as one revisioned mutation."""

        with self._lock:
            if self.get_document(document_id) is None:
                return False
            with self.transaction() as conn:
                conn.execute(
                    """
                    UPDATE sources
                    SET document_filename_snapshot = COALESCE(
                            document_filename_snapshot,
                            (
                                SELECT filename
                                FROM documents
                                WHERE documents.id = sources.document_id
                            )
                        ),
                        document_sha256_snapshot = COALESCE(
                            document_sha256_snapshot,
                            (SELECT sha256 FROM documents WHERE documents.id = sources.document_id)
                        ),
                        chunk_index_snapshot = COALESCE(
                            chunk_index_snapshot,
                            (
                                SELECT chunk_index
                                FROM chunks
                                WHERE chunks.id = sources.chunk_id
                            )
                        )
                    WHERE document_id = ?
                    """,
                    (document_id,),
                )
                self.clear_document_content(document_id, connection=conn)
                deleted = conn.execute(
                    "DELETE FROM documents WHERE id = ?",
                    (document_id,),
                ).rowcount
                if not deleted:
                    return False
                revision = self.increment_corpus_revision(conn)
                self.record_audit(
                    entity_type="document",
                    entity_id=document_id,
                    action="delete",
                    details={"corpus_revision": revision},
                    connection=conn,
                )
            return True

    def table_names(self) -> set[str]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')"
            ).fetchall()
            return {str(row["name"]) for row in rows}


def init_database(path_or_settings: str | Path | Settings) -> Database:
    """Create local directories, initialize SQLite, and return a ready database."""

    if isinstance(path_or_settings, Settings):
        path_or_settings.ensure_directories()
        return Database(path_or_settings.db_path)
    return Database(path_or_settings)


initialize_database = init_database


__all__ = [
    "Database",
    "SCHEMA_STATEMENTS",
    "SCHEMA_VERSION",
    "init_database",
    "initialize_database",
    "utc_now",
]
