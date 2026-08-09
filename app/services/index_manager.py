"""Versioned index state, promotion and rollback primitives."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from ..database import Database

INDEX_STATES = frozenset(
    {"building", "validating", "shadow", "canary", "active", "degraded", "rolled_back", "failed"}
)
PROMOTABLE_STATES = frozenset({"shadow", "canary", "degraded", "validated", "active"})


@dataclass(frozen=True, slots=True)
class IndexManifest:
    index_version: str
    corpus_snapshot_hash: str
    corpus_revision_start: int
    corpus_revision_end: int
    document_count: int
    chunk_count: int
    chunking_version: str
    chunk_size: int
    chunk_overlap: int
    splitter_type: str
    embedding_provider: str
    embedding_model_name: str
    embedding_model_revision: str
    embedding_dimension: int
    embedding_normalize: bool
    distance_metric: str
    collection_name: str
    build_command: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "index_version",
        "corpus_snapshot_hash",
        "corpus_revision_start",
        "corpus_revision_end",
        "document_count",
        "chunk_count",
        "chunking_version",
        "chunk_size",
        "chunk_overlap",
        "splitter_type",
        "embedding_provider",
        "embedding_model_name",
        "embedding_model_revision",
        "embedding_dimension",
        "embedding_normalize",
        "distance_metric",
        "collection_name",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(f"manifest incompleto: {', '.join(missing)}")
    if not str(manifest["index_version"]).strip() or int(manifest["chunk_count"]) < 0:
        raise ValueError("manifest contiene conteos o version invalidos")
    if int(manifest["corpus_revision_end"]) < int(manifest["corpus_revision_start"]):
        raise ValueError("revision final anterior a la inicial")


class IndexManager:
    def __init__(self, database: Database, *, actor: str = "local-operator") -> None:
        self.database = database
        self.actor = actor

    def active_version(self) -> str | None:
        return self.database.get_meta("rag_active_index_version") or None

    def register(
        self,
        manifest: IndexManifest | dict[str, Any],
        *,
        status: str = "building",
    ) -> dict[str, Any]:
        payload = manifest.to_dict() if isinstance(manifest, IndexManifest) else dict(manifest)
        validate_manifest(payload)
        if status not in INDEX_STATES and status != "validated":
            raise ValueError(f"estado de indice invalido: {status}")
        self.database.upsert_rag_index(
            index_version=str(payload["index_version"]),
            backend="chroma" if payload.get("embedding_provider") != "none" else "fts5",
            manifest=payload,
            status=status,
            lag=0,
        )
        return payload

    def promote(self, index_version: str, *, reason: str, status: str = "active") -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reason is required for promotion or rollback")
        if status not in {"active", "rolled_back"}:
            raise ValueError("promotion status must be active or rolled_back")
        candidate = self.database.get_rag_index(index_version)
        if candidate is None:
            raise ValueError(f"index version not found: {index_version}")
        validate_manifest(candidate["manifest"])
        previous = self.active_version()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if previous and previous != index_version:
            previous_record = self.database.get_rag_index(previous)
            if previous_record:
                self.database.upsert_rag_index(
                    index_version=previous,
                    backend=str(previous_record["backend"]),
                    manifest=previous_record["manifest"],
                    status="rolled_back" if status == "active" else "degraded",
                    lag=int(previous_record.get("lag") or 0),
                )
        self.database.upsert_rag_index(
            index_version=index_version,
            backend=str(candidate["backend"]),
            manifest=candidate["manifest"],
            status="active" if status == "active" else "rolled_back",
            lag=int(candidate.get("lag") or 0),
            activated_at=now,
        )
        self.database.set_meta(
            "rag_active_index_version", index_version if status == "active" else ""
        )
        self.database.set_meta(
            "rag_last_operation",
            json.dumps(
                {
                    "operation": "promote" if status == "active" else "rollback",
                    "actor": self.actor,
                    "previous_version": previous,
                    "new_version": index_version,
                    "reason": reason,
                    "created_at": now,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        return {
            "active_version": self.active_version(),
            "previous_version": previous,
            "index_version": index_version,
            "reason": reason,
            "actor": self.actor,
        }

    def status(self) -> dict[str, Any]:
        indexes = self.database.list_rag_indexes()
        return {
            "active_version": self.active_version(),
            "indexes": indexes,
            "corpus_revision": self.database.get_corpus_revision(),
            "last_operation": self.database.get_meta("rag_last_operation"),
            "sqlite_authority": True,
            "fallback": "fts5",
        }


def manifest_from_database(database: Database, settings: Any, index_version: str) -> IndexManifest:
    chunks = database.list_eligible_chunks()
    snapshot = hashlib.sha256(
        "\n".join(f"{row['id']}:{row['sha256']}" for row in chunks).encode("utf-8")
    ).hexdigest()
    return IndexManifest(
        index_version=index_version,
        corpus_snapshot_hash=snapshot,
        corpus_revision_start=database.get_corpus_revision(),
        corpus_revision_end=database.get_corpus_revision(),
        document_count=len({str(row["document_id"]) for row in chunks}),
        chunk_count=len(chunks),
        chunking_version=settings.rag.chunking_version,
        chunk_size=settings.rag.chunk_size,
        chunk_overlap=settings.rag.chunk_overlap,
        splitter_type=settings.rag.splitter_type,
        embedding_provider=settings.rag.embedding_provider,
        embedding_model_name=settings.rag.embedding_model_name,
        embedding_model_revision=settings.rag.embedding_model_revision,
        embedding_dimension=settings.rag.embedding_dimension,
        embedding_normalize=settings.rag.embedding_normalize,
        distance_metric=settings.rag.distance_metric,
        collection_name=settings.rag.rag_index_name,
        build_command="python -m scripts.build_rag_index",
    )


__all__ = [
    "INDEX_STATES",
    "IndexManager",
    "IndexManifest",
    "manifest_from_database",
    "validate_manifest",
]
