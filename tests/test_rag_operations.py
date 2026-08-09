from __future__ import annotations

import pytest

from app.config import Settings
from app.database import init_database
from app.services.index_manager import IndexManager, IndexManifest, validate_manifest


def _manifest(version: str) -> IndexManifest:
    return IndexManifest(
        index_version=version,
        corpus_snapshot_hash="hash",
        corpus_revision_start=0,
        corpus_revision_end=0,
        document_count=0,
        chunk_count=0,
        chunking_version="c0",
        chunk_size=1200,
        chunk_overlap=200,
        splitter_type="recursive_es_v2",
        embedding_provider="none",
        embedding_model_name="none",
        embedding_model_revision="none",
        embedding_dimension=1024,
        embedding_normalize=True,
        distance_metric="cosine",
        collection_name="fts5",
    )


def test_manifest_and_promotion_are_idempotent_and_keep_previous_version(tmp_path):
    database = init_database(Settings(data_dir=tmp_path))
    try:
        manager = IndexManager(database, actor="test")
        manager.register(_manifest("v1"), status="validated")
        manager.register(_manifest("v2"), status="validated")
        assert manager.promote("v1", reason="baseline")['active_version'] == "v1"
        result = manager.promote("v2", reason="canary passed")
        assert result["active_version"] == "v2"
        assert database.get_rag_index("v1")["status"] == "rolled_back"
        manager.promote("v1", reason="rollback incident", status="rolled_back")
        assert manager.active_version() is None
        assert database.get_rag_index("v2") is not None
    finally:
        database.close()


def test_promotion_rejects_missing_reason_and_incomplete_manifest(tmp_path):
    database = init_database(Settings(data_dir=tmp_path))
    try:
        manager = IndexManager(database)
        with pytest.raises(ValueError, match="incompleto"):
            validate_manifest({"index_version": "x"})
        manager.register(_manifest("v1"), status="validated")
        with pytest.raises(ValueError, match="reason"):
            manager.promote("v1", reason="")
    finally:
        database.close()
