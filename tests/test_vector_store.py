from __future__ import annotations

import pytest

from app.services.vector_store import (
    IndexManifest,
    InMemoryVectorStore,
    VectorRecord,
    cosine_similarity,
    hash_embedding,
)


def manifest() -> IndexManifest:
    return IndexManifest(
        index_version="test-v1",
        chunking_version="recursive_es_v2",
        embedding_provider="none",
        embedding_model_name="hash-test",
        embedding_model_revision="local",
        embedding_dimension=8,
    )


def test_vector_ids_are_idempotent_and_queries_are_stably_ordered():
    store = InMemoryVectorStore(manifest())
    record = VectorRecord(
        id="chunk-a",
        document_id="doc-a",
        embedding=hash_embedding("herida cuidado", 8),
        metadata={"corpus_revision": 0},
    )
    store.upsert([record, record])
    assert store.count == 1
    hits = store.query(store.embed_query("herida"), limit=5, fetch_k=5)
    assert [hit.id for hit in hits] == ["chunk-a"]
    assert hits[0].similarity > 0


def test_vector_store_rejects_dimension_mismatch_and_deletes_by_document():
    store = InMemoryVectorStore(manifest())
    with pytest.raises(ValueError, match="dimension"):
        store.upsert(
            [
                VectorRecord(
                    id="chunk-b",
                    document_id="doc-b",
                    embedding=(1.0, 2.0),
                )
            ]
        )
    store.upsert(
        [
            VectorRecord(
                id="chunk-b",
                document_id="doc-b",
                embedding=hash_embedding("dolor", 8),
            )
        ]
    )
    store.delete_by_document("doc-b")
    assert store.count == 0


def test_cosine_similarity_is_normalized():
    assert cosine_similarity((1.0, 0.0), (2.0, 0.0)) == pytest.approx(1.0)
