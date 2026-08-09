from __future__ import annotations

from pathlib import Path

from app.schemas import ExtractedPage
from app.services.loaders import SourceFile, to_langchain_documents


def test_loader_conversion_preserves_pages_offsets_ids_and_ocr_filter():
    source = SourceFile(
        document_id="doc-1",
        filename="guia local.md",
        sha256="sha",
        path=Path("guia local.md"),
    )
    documents = to_langchain_documents(
        source,
        [
            ExtractedPage(page_number=1, text="Texto de la guía", needs_ocr=False),
            ExtractedPage(page_number=2, text="", needs_ocr=True),
        ],
        index_version="idx-v1",
        chunk_size=1200,
        chunk_overlap=0,
    )
    assert len(documents) == 1
    metadata = documents[0].metadata
    assert metadata["document_id"] == "doc-1"
    assert metadata["page_number"] == 1
    assert metadata["chunk_id"]
    assert metadata["start_char"] == 0
    assert metadata["end_char"] > metadata["start_char"]
    assert metadata["index_version"] == "idx-v1"


def test_loader_does_not_render_html_like_markdown():
    source = SourceFile(document_id="doc-1", filename="x.md")
    documents = to_langchain_documents(
        source,
        [ExtractedPage(page_number=1, text="<script>alert(1)</script>", needs_ocr=False)],
        chunk_overlap=0,
    )
    assert documents[0].page_content.startswith("<script>")
