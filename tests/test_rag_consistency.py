from __future__ import annotations

from app.config import Settings
from app.database import init_database
from app.services.documents import DocumentService
from app.services.rag import RagService
from app.services.vector_store import IndexManifest, InMemoryVectorStore


def test_vector_retrieval_hydrates_from_sqlite_and_respects_delete(tmp_path):
    database = init_database(tmp_path / "app.sqlite3")
    settings = Settings(data_dir=tmp_path)
    store = InMemoryVectorStore(
        IndexManifest(
            index_version="test-v1",
            chunking_version="recursive_es_v2",
            embedding_provider="none",
            embedding_model_name="hash-test",
            embedding_model_revision="local",
            embedding_dimension=32,
            corpus_revision=0,
        )
    )
    documents = DocumentService(database, settings, vector_store=store)
    record = documents.upload(b"Vigila la herida y reporta dolor intenso.", "guide.txt")
    assert record.enabled is True

    rag = RagService(database, vector_store=store, settings=settings)
    results = rag.search("herida", limit=2)
    assert results
    assert results[0].filename == "guide.txt"
    assert results[0].text.startswith("Vigila")
    assert results[0].corpus_revision == database.get_corpus_revision()

    assert documents.delete(record.id) is True
    assert rag.search("herida", limit=2) == []


def test_disabled_documents_are_never_hydrated_from_a_vector_hit(tmp_path):
    database = init_database(tmp_path / "app.sqlite3")
    settings = Settings(data_dir=tmp_path)
    store = InMemoryVectorStore(
        IndexManifest(
            index_version="test-v1",
            chunking_version="recursive_es_v2",
            embedding_provider="none",
            embedding_model_name="hash-test",
            embedding_model_revision="local",
            embedding_dimension=32,
        )
    )
    documents = DocumentService(database, settings, vector_store=store)
    record = documents.upload(b"La herida requiere observacion.", "guide.txt")
    documents.set_enabled(record.id, False)
    assert RagService(database, vector_store=store, settings=settings).search("herida") == []
