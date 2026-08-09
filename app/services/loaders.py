"""Document loader adapters that preserve the local ingestion contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from ..schemas import ExtractedPage
from .ingestion import chunk_pages, extract_pages

try:  # Optional until the small LangChain adapter is installed in a deployment.
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover - exercised when optional dependency is absent.
    @dataclass(frozen=True, slots=True)
    class Document:  # type: ignore[no-redef]
        page_content: str
        metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class SourceFile:
    document_id: str
    filename: str
    sha256: str = ""
    path: Path | None = None


class DocumentLoader(Protocol):
    def load(self, source: SourceFile) -> list[ExtractedPage]: ...


class LocalDocumentLoader:
    """Use PyMuPDF/TXT/MD extraction without rendering or executing content."""

    def load(self, source: SourceFile) -> list[ExtractedPage]:
        if source.path is None:
            raise ValueError("SourceFile.path is required for local loading")
        return extract_pages(source.path)


def to_langchain_documents(
    source: SourceFile,
    pages: Sequence[ExtractedPage],
    *,
    index_version: str = "baseline-fts5-v1",
    chunking_version: str = "recursive_es_v2",
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> list[Document]:
    """Convert usable pages to citation-preserving LangChain Documents."""

    documents: list[Document] = []
    for page in pages:
        if page.needs_ocr or not page.text.strip():
            continue
        chunks = chunk_pages(
            [page],
            document_id=source.document_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        for chunk in chunks:
            documents.append(
                Document(
                    page_content=chunk.text,
                    metadata={
                        "document_id": source.document_id,
                        "filename": source.filename,
                        "sha256": source.sha256,
                        "page_number": chunk.page_number,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "chunking_version": chunking_version,
                        "index_version": index_version,
                        "needs_ocr": False,
                    },
                )
            )
    return documents


__all__ = [
    "Document",
    "DocumentLoader",
    "LocalDocumentLoader",
    "SourceFile",
    "to_langchain_documents",
]
