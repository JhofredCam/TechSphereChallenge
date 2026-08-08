"""Document upload, processing, replacement, and deletion lifecycle."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import BinaryIO

from ..config import Settings
from ..database import Database, utc_now
from ..schemas import DocumentRecord, DocumentStatus
from .ingestion import (
    chunk_pages,
    document_id_for_bytes,
    extract_document,
    guess_mime_type,
    page_id_for,
)

_INVALID_WINDOWS_FILENAME_CHARS = frozenset('<>:"/\\|?*')
_WINDOWS_RESERVED_BASENAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
        "COM¹",
        "COM²",
        "COM³",
        "LPT¹",
        "LPT²",
        "LPT³",
    }
)
_MAX_STORAGE_PATH_LENGTH = 240
_MAX_FILENAME_COMPONENT_LENGTH = 255


def _is_windows_reserved_name(filename: str) -> bool:
    basename = filename.split(".", 1)[0]
    return basename.upper() in _WINDOWS_RESERVED_BASENAMES


def safe_storage_filename(
    filename: str | None,
    *,
    storage_directory: str | Path | None = None,
    document_id: str | None = None,
) -> str:
    """Return one deterministic filename safe for local Windows and POSIX storage."""

    raw = str(filename or "document").replace("\\", "/")
    name = raw.rsplit("/", 1)[-1].strip()
    if not name or name in {".", ".."}:
        name = "document"
    name = "".join(
        "_" if character in _INVALID_WINDOWS_FILENAME_CHARS or ord(character) < 32 else character
        for character in name
    ).strip(" .")
    if not name:
        name = "document"
    if _is_windows_reserved_name(name):
        name = f"_{name}"

    maximum_length = _MAX_FILENAME_COMPONENT_LENGTH
    storage_path: Path | None = None
    if storage_directory is not None:
        storage_path = Path(storage_directory)
        maximum_length = min(
            maximum_length,
            max(1, _MAX_STORAGE_PATH_LENGTH - len(str(storage_path)) - 1),
        )

    if len(name) > maximum_length:
        suffix = Path(name).suffix
        stem = name[: -len(suffix)] if suffix else name
        marker_seed = str(document_id) if document_id else name
        marker = f"-{hashlib.sha256(marker_seed.encode('utf-8')).hexdigest()[:12]}"
        suffix_limit = max(0, maximum_length - len(marker) - 1)
        if len(suffix) > suffix_limit:
            suffix = suffix[-suffix_limit:] if suffix_limit else ""
        marker = marker[: max(0, maximum_length - len(suffix) - 1)]
        stem_limit = max(1, maximum_length - len(marker) - len(suffix))
        stem = stem[:stem_limit].rstrip(" .") or "d"
        name = f"{stem}{marker}{suffix}"

    if storage_path is not None:
        while len(str(storage_path / name)) > _MAX_STORAGE_PATH_LENGTH and len(name) > 1:
            name = name[:-1].rstrip(" .") or "d"
    return name


class DocumentService:
    """Synchronously manage local documents and their searchable content."""

    def __init__(
        self,
        database: Database,
        settings: Settings | str | Path | None = None,
    ) -> None:
        self.database = database
        if settings is None:
            settings = Settings(data_dir=database.path.parent)
        elif not isinstance(settings, Settings):
            settings = Settings(data_dir=Path(settings))
        self.settings = settings
        self.settings.ensure_directories()

    @staticmethod
    def _safe_filename(
        filename: str | None,
        *,
        storage_directory: str | Path | None = None,
        document_id: str | None = None,
    ) -> str:
        return safe_storage_filename(
            filename,
            storage_directory=storage_directory,
            document_id=document_id,
        )

    @staticmethod
    def _read_source(
        source: str | Path | bytes | bytearray | BinaryIO,
        filename: str | None,
    ) -> tuple[bytes, str]:
        if isinstance(source, (str, Path)):
            source_path = Path(source)
            return source_path.read_bytes(), filename or source_path.name
        if isinstance(source, (bytes, bytearray)):
            if not filename:
                raise ValueError("filename is required when uploading bytes")
            return bytes(source), filename

        reader = getattr(source, "read", None)
        if reader is None or not callable(reader):
            raise TypeError("source must be a path, bytes, or binary file object")
        content = reader()
        if isinstance(content, str):
            content = content.encode("utf-8")
        if not isinstance(content, (bytes, bytearray)):
            raise TypeError("file object's read() must return bytes")
        source_name = filename or getattr(source, "filename", None)
        if not source_name:
            raise ValueError("filename is required when uploading a file object")
        return bytes(content), str(source_name)

    def upload(
        self,
        source: str | Path | bytes | bytearray | BinaryIO,
        filename: str | None = None,
        *,
        mime_type: str | None = None,
        process: bool = True,
    ) -> DocumentRecord:
        """Store an upload by content hash and optionally process it immediately."""

        content, original_name = self._read_source(source, filename)
        if len(content) > self.settings.max_upload_bytes:
            raise ValueError(
                f"document exceeds the configured limit of "
                f"{self.settings.max_upload_bytes} bytes"
            )
        digest = document_id_for_bytes(content)
        existing = self.database.get_document_by_hash(digest)
        if existing is not None:
            if process and existing.status in {
                DocumentStatus.PROCESSING,
                DocumentStatus.ERROR,
            }:
                return self.process(existing.id)
            return existing

        document_dir = self.settings.documents_dir / digest
        document_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(
            original_name,
            storage_directory=document_dir,
            document_id=digest,
        )
        stored_path = document_dir / safe_name
        stored_path.write_bytes(content)
        record: DocumentRecord
        try:
            record = self.database.create_document(
                document_id=digest,
                sha256=digest,
                filename=safe_name,
                stored_path=str(stored_path),
                mime_type=mime_type or guess_mime_type(safe_name),
                size_bytes=len(content),
            )
            self.database.record_audit(
                entity_type="document",
                entity_id=digest,
                action="upload",
                details={"filename": safe_name, "size_bytes": len(content)},
            )
        except sqlite3.IntegrityError:
            # A concurrent identical upload may have won the unique hash race.
            existing = self.database.get_document_by_hash(digest)
            if existing is None:
                raise
            return self.process(existing.id) if process else existing

        return self.process(record.id) if process else record

    def process(self, document_id: str, *, force: bool = False) -> DocumentRecord:
        """Extract and index one document, preserving an explicit error status."""

        record = self.database.get_document(document_id)
        if record is None:
            raise KeyError(f"unknown document: {document_id}")
        if not force and record.status in {
            DocumentStatus.AVAILABLE,
            DocumentStatus.NEEDS_OCR,
        }:
            return record

        try:
            extraction = extract_document(record.stored_path)
            chunks = chunk_pages(
                extraction.pages,
                document_id=document_id,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
            with self.database.transaction() as connection:
                self.database.clear_document_content(document_id, connection=connection)
                for page in extraction.pages:
                    page_id = page_id_for(document_id, page.page_number)
                    self.database.insert_page(
                        page_id=page_id,
                        document_id=document_id,
                        page_number=page.page_number,
                        text=page.text,
                        needs_ocr=page.needs_ocr,
                        connection=connection,
                    )
                for chunk in chunks:
                    self.database.insert_chunk(
                        chunk_id=chunk.id,
                        document_id=document_id,
                        page_id=page_id_for(document_id, chunk.page_number),
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        start_char=chunk.start_char,
                        end_char=chunk.end_char,
                        connection=connection,
                    )
                revision = self.database.increment_corpus_revision(connection)
                self.database.update_document_status(
                    document_id,
                    extraction.status,
                    processed_at=utc_now(),
                    connection=connection,
                )
                self.database.record_audit(
                    entity_type="document",
                    entity_id=document_id,
                    action="process",
                    details={
                        "status": extraction.status.value,
                        "pages": len(extraction.pages),
                        "chunks": len(chunks),
                        "corpus_revision": revision,
                    },
                    connection=connection,
                )
        except Exception as exc:
            error = str(exc)[:1000] or exc.__class__.__name__
            with self.database.transaction() as connection:
                self.database.update_document_status(
                    document_id,
                    DocumentStatus.ERROR,
                    error=error,
                    processed_at=None,
                    connection=connection,
                )
                self.database.record_audit(
                    entity_type="document",
                    entity_id=document_id,
                    action="process_error",
                    details={"error": error},
                    connection=connection,
                )
            updated = self.database.get_document(document_id)
            if updated is None:
                raise RuntimeError("document disappeared while recording an ingestion error")
            return updated

        updated = self.database.get_document(document_id)
        if updated is None:
            raise RuntimeError("document disappeared after processing")
        return updated

    def get(self, document_id: str) -> DocumentRecord | None:
        return self.database.get_document(document_id)

    def list(self, status: DocumentStatus | str | None = None) -> list[DocumentRecord]:
        return self.database.list_documents(status)

    def delete(self, document_id: str) -> bool:
        record = self.database.get_document(document_id)
        if record is None:
            return False
        deleted = self.database.delete_document(document_id)
        if not deleted:
            return False
        stored_path = Path(record.stored_path)
        cleanup_error: str | None = None
        try:
            stored_path.resolve().relative_to(self.settings.documents_dir.resolve())
        except (OSError, RuntimeError, ValueError) as exc:
            if isinstance(exc, ValueError):
                cleanup_error = "stored path is outside the configured documents directory"
            else:
                cleanup_error = str(exc).strip() or exc.__class__.__name__
        else:
            try:
                stored_path.unlink(missing_ok=True)
                try:
                    stored_path.parent.rmdir()
                except OSError as exc:
                    cleanup_error = str(exc).strip() or exc.__class__.__name__
            except OSError as exc:
                cleanup_error = str(exc).strip() or exc.__class__.__name__
        if cleanup_error:
            self.database.record_audit(
                entity_type="document",
                entity_id=document_id,
                action="delete_storage_error",
                details={
                    "error": cleanup_error[:1000],
                    "stored_path": str(stored_path),
                },
            )
        return True

    @property
    def corpus_revision(self) -> int:
        return self.database.get_corpus_revision()


def upload_document(
    database: Database,
    source: str | Path | bytes | bytearray | BinaryIO,
    filename: str | None = None,
    *,
    settings: Settings | str | Path | None = None,
    mime_type: str | None = None,
    process: bool = True,
) -> DocumentRecord:
    """Functional convenience wrapper for API/bootstrap integrations."""

    return DocumentService(database, settings).upload(
        source,
        filename,
        mime_type=mime_type,
        process=process,
    )


def process_document(
    database: Database,
    document_id: str,
    *,
    settings: Settings | str | Path | None = None,
    force: bool = False,
) -> DocumentRecord:
    return DocumentService(database, settings).process(document_id, force=force)


def delete_document(
    database: Database,
    document_id: str,
    *,
    settings: Settings | str | Path | None = None,
) -> bool:
    return DocumentService(database, settings).delete(document_id)


def list_documents(
    database: Database,
    *,
    settings: Settings | str | Path | None = None,
    status: DocumentStatus | str | None = None,
) -> list[DocumentRecord]:
    return DocumentService(database, settings).list(status)


__all__ = [
    "DocumentService",
    "delete_document",
    "list_documents",
    "process_document",
    "safe_storage_filename",
    "upload_document",
]
