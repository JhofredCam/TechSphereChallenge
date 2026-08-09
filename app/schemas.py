"""Small, dependency-light contracts shared by the local services."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    AVAILABLE = "available"
    NEEDS_OCR = "needs_ocr"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    id: str
    filename: str
    stored_path: str
    sha256: str
    size_bytes: int
    mime_type: str
    status: DocumentStatus | str
    error: str | None = None
    created_at: str | None = None
    processed_at: str | None = None
    enabled: bool = False
    page_count: int = 0
    chunk_count: int = 0

    @property
    def document_id(self) -> str:
        return self.id

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "DocumentRecord":
        raw_status = row["status"]
        try:
            status: DocumentStatus | str = DocumentStatus(raw_status)
        except ValueError:
            status = str(raw_status)
        try:
            raw_enabled = row["enabled"]
        except (KeyError, IndexError):
            raw_enabled = 0
        try:
            enabled = bool(int(raw_enabled or 0))
        except (TypeError, ValueError):
            enabled = bool(raw_enabled)
        try:
            raw_page_count = row["page_count"]
        except (KeyError, IndexError):
            raw_page_count = 0
        try:
            raw_chunk_count = row["chunk_count"]
        except (KeyError, IndexError):
            raw_chunk_count = 0
        return cls(
            id=str(row["id"]),
            filename=str(row["filename"]),
            stored_path=str(row["stored_path"]),
            sha256=str(row["sha256"]),
            size_bytes=int(row["size_bytes"]),
            mime_type=str(row["mime_type"]),
            status=status,
            error=row["error"],
            created_at=row["created_at"],
            processed_at=row["processed_at"],
            enabled=enabled,
            page_count=int(raw_page_count or 0),
            chunk_count=int(raw_chunk_count or 0),
        )

    @property
    def status_value(self) -> str:
        return self.status.value if isinstance(self.status, DocumentStatus) else str(self.status)

    @property
    def rag_eligible(self) -> bool:
        return self.status_value == DocumentStatus.AVAILABLE.value and self.enabled

    @property
    def available(self) -> bool:
        return self.status_value == DocumentStatus.AVAILABLE.value

    @property
    def needs_ocr(self) -> bool:
        return self.status_value == DocumentStatus.NEEDS_OCR.value

    @property
    def preview_available(self) -> bool:
        return self.available


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page_number: int
    text: str
    needs_ocr: bool = False


@dataclass(frozen=True, slots=True)
class ExtractedChunk:
    id: str
    document_id: str
    page_number: int
    chunk_index: int
    text: str
    start_char: int
    end_char: int


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    pages: tuple[ExtractedPage, ...]
    status: DocumentStatus
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    document_id: str
    filename: str
    page_number: int
    chunk_id: str
    text: str
    score: float
    citation: str
    corpus_revision: int
    chunk_index: int | None = None

    @property
    def source(self) -> str:
        return self.citation


@dataclass(frozen=True, slots=True)
class DatasetTableReport:
    path: str
    sheet_name: str | None
    headers: tuple[str, ...]
    row_count: int
    errors: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True, slots=True)
class DatasetValidationReport:
    tables: tuple[DatasetTableReport, ...]
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors and all(table.valid for table in self.tables)

    @property
    def row_counts(self) -> dict[str, int]:
        return {table.path: table.row_count for table in self.tables}


__all__ = [
    "DatasetTableReport",
    "DatasetValidationReport",
    "DocumentRecord",
    "DocumentStatus",
    "ExtractedChunk",
    "ExtractedPage",
    "ExtractionResult",
    "SearchResult",
]
