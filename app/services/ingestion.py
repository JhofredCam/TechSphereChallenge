"""Recursive-safe extraction and deterministic chunking for local documents."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Iterator

from ..schemas import DocumentStatus, ExtractedChunk, ExtractedPage, ExtractionResult

SUPPORTED_SUFFIXES = frozenset({".pdf", ".txt", ".md"})


class IngestionError(RuntimeError):
    """Base error for a source that cannot be extracted safely."""


class UnsupportedFileTypeError(IngestionError):
    pass


class PdfDependencyError(IngestionError):
    pass


def normalize_text(value: str) -> str:
    """Normalize whitespace and line endings without changing searchable accents."""

    return re.sub(r"\s+", " ", value.replace("\r\n", "\n").replace("\r", "\n")).strip()


def normalize_for_search(value: str) -> str:
    """Return a case- and diacritic-insensitive value suitable for FTS queries."""

    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return normalize_text(without_marks)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def document_id_for_bytes(data: bytes) -> str:
    """Content-address a document so duplicate uploads have one identity."""

    return sha256_hex(data)


def page_id_for(document_id: str, page_number: int) -> str:
    return sha256_hex(f"page\0{document_id}\0{page_number}".encode("utf-8"))


def chunk_id_for(
    document_id: str,
    page_number: int,
    chunk_index: int,
    text: str,
) -> str:
    payload = f"chunk\0{document_id}\0{page_number}\0{chunk_index}\0{text}"
    return sha256_hex(payload.encode("utf-8"))


def iter_supported_files(root: str | Path) -> Iterator[Path]:
    """Yield supported files recursively, including paths containing spaces.

    Symlink files are ignored so a corpus cannot unexpectedly escape its configured root.
    """

    source = Path(root)
    if source.is_file():
        if source.suffix.lower() in SUPPORTED_SUFFIXES and not source.is_symlink():
            yield source
        return
    if not source.is_dir():
        raise FileNotFoundError(source)
    for candidate in sorted(source.rglob("*"), key=lambda path: str(path).casefold()):
        if candidate.is_file() and not candidate.is_symlink():
            if candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                yield candidate


def _read_text_file(path: Path) -> str:
    # UTF-8 is the corpus format; replacement keeps ingestion deterministic for a bad byte.
    return path.read_bytes().decode("utf-8-sig", errors="replace")


def _extract_pdf_pages(path: Path) -> list[ExtractedPage]:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PdfDependencyError(
            "PyMuPDF is required to ingest PDF files; install the 'pymupdf' package"
        ) from exc

    pages: list[ExtractedPage] = []
    try:
        pdf = fitz.open(path)
        try:
            for index, page in enumerate(pdf, start=1):
                text = page.get_text("text") or ""
                text = str(text).replace("\r\n", "\n").replace("\r", "\n")
                pages.append(
                    ExtractedPage(
                        page_number=index,
                        text=text,
                        needs_ocr=not bool(text.strip()),
                    )
                )
        finally:
            pdf.close()
    except IngestionError:
        raise
    except Exception as exc:  # PyMuPDF exposes several concrete exception types by version.
        raise IngestionError(f"could not extract PDF {path.name}: {exc}") from exc
    return pages


def extract_pages(path: str | Path) -> list[ExtractedPage]:
    """Extract one-based pages from PDF, TXT, or Markdown files."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_pages(source)
    if suffix in {".txt", ".md"}:
        text = _read_text_file(source).replace("\r\n", "\n").replace("\r", "\n")
        return [ExtractedPage(page_number=1, text=text, needs_ocr=not bool(text.strip()))]
    raise UnsupportedFileTypeError(f"unsupported document type: {source.suffix or '<none>'}")


def extract_document(path: str | Path) -> ExtractionResult:
    """Extract pages and explicitly mark sources that have no usable text."""

    pages = tuple(extract_pages(path))
    has_text = any(page.text.strip() for page in pages)
    status = DocumentStatus.AVAILABLE if has_text else DocumentStatus.NEEDS_OCR
    return ExtractionResult(pages=pages, status=status)


def chunk_pages(
    pages: Iterable[ExtractedPage],
    *,
    document_id: str = "document",
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[ExtractedChunk]:
    """Split each page independently and retain exact page and character metadata."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between zero and chunk_size - 1")

    chunks: list[ExtractedChunk] = []
    for page in pages:
        text = page.text
        if not text.strip():
            continue
        start = 0
        chunk_index = 0
        while start < len(text):
            raw_end = min(start + chunk_size, len(text))
            raw_text = text[start:raw_end]
            left_trimmed = raw_text.lstrip()
            right_trimmed = left_trimmed.rstrip()
            chunk_text = right_trimmed
            if chunk_text:
                content_start = start + (len(raw_text) - len(left_trimmed))
                content_end = content_start + len(chunk_text)
                chunks.append(
                    ExtractedChunk(
                        id=chunk_id_for(
                            document_id,
                            page.page_number,
                            chunk_index,
                            chunk_text,
                        ),
                        document_id=document_id,
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        text=chunk_text,
                        start_char=content_start,
                        end_char=content_end,
                    )
                )
                chunk_index += 1
            if raw_end >= len(text):
                break
            next_start = raw_end - chunk_overlap
            start = max(next_start, start + 1)
    return chunks


def guess_mime_type(path: str | Path) -> str:
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "application/octet-stream"


# Explicit aliases make the extraction boundary easy to discover for callers.
extract_file_pages = extract_pages
iter_document_files = iter_supported_files
chunk_text = chunk_pages
ingest_file = extract_document


__all__ = [
    "SUPPORTED_SUFFIXES",
    "IngestionError",
    "PdfDependencyError",
    "UnsupportedFileTypeError",
    "chunk_id_for",
    "chunk_pages",
    "chunk_text",
    "document_id_for_bytes",
    "extract_document",
    "extract_file_pages",
    "extract_pages",
    "guess_mime_type",
    "ingest_file",
    "iter_document_files",
    "iter_supported_files",
    "normalize_for_search",
    "normalize_text",
    "page_id_for",
    "sha256_hex",
]
