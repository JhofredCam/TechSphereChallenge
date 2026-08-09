"""Versioned vector-store contracts with an optional Chroma adapter.

The module keeps Chroma optional for the challenge-local profile. SQLite remains
the authority for document status, text, citations, and corpus revision.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence


class VectorStoreUnavailable(RuntimeError):
    """Raised when a configured vector backend cannot be opened safely."""


@dataclass(frozen=True, slots=True)
class IndexManifest:
    index_version: str
    chunking_version: str
    embedding_provider: str
    embedding_model_name: str
    embedding_model_revision: str
    embedding_dimension: int
    distance_metric: str = "cosine"
    collection_name: str = "techsphere_rag"
    corpus_revision: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "IndexManifest":
        return cls(
            index_version=str(value["index_version"]),
            chunking_version=str(value["chunking_version"]),
            embedding_provider=str(value["embedding_provider"]),
            embedding_model_name=str(value["embedding_model_name"]),
            embedding_model_revision=str(value.get("embedding_model_revision", "unset")),
            embedding_dimension=int(value["embedding_dimension"]),
            distance_metric=str(value.get("distance_metric", "cosine")),
            collection_name=str(value.get("collection_name", "techsphere_rag")),
            corpus_revision=int(value.get("corpus_revision", 0)),
        )


@dataclass(frozen=True, slots=True)
class VectorRecord:
    id: str
    embedding: tuple[float, ...]
    document_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.document_id:
            raise ValueError("vector id and document id are required")
        if not self.embedding:
            raise ValueError("embedding cannot be empty")


@dataclass(frozen=True, slots=True)
class VectorHit:
    id: str
    document_id: str
    distance: float
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(Protocol):
    def upsert(self, records: Sequence[VectorRecord]) -> None: ...

    def query(self, vector: Sequence[float], limit: int, fetch_k: int) -> list[VectorHit]: ...

    def delete_by_document(self, document_id: str) -> None: ...

    def delete_by_ids(self, chunk_ids: Sequence[str]) -> None: ...

    def collection_manifest(self) -> IndexManifest: ...


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left or not right:
        raise ValueError("vectors must have the same non-zero dimension")
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def hash_embedding(value: str, dimension: int = 32) -> tuple[float, ...]:
    """Create a deterministic local embedding for contract tests and offline fallback."""

    if dimension <= 0:
        raise ValueError("dimension must be positive")
    values = [0.0] * dimension
    for token in str(value).casefold().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        values[index] += 1.0 if digest[4] % 2 else -1.0
    norm = math.sqrt(sum(item * item for item in values)) or 1.0
    return tuple(item / norm for item in values)


class InMemoryVectorStore:
    """Deterministic store used by tests and the local migration preflight."""

    def __init__(self, manifest: IndexManifest) -> None:
        self._manifest = manifest
        self._records: dict[str, VectorRecord] = {}

    def embed_query(self, query: str) -> tuple[float, ...]:
        return hash_embedding(query, self._manifest.embedding_dimension)

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        for record in records:
            if len(record.embedding) != self._manifest.embedding_dimension:
                raise ValueError("embedding dimension does not match the index manifest")
            self._records[record.id] = record

    def query(self, vector: Sequence[float], limit: int, fetch_k: int) -> list[VectorHit]:
        if len(vector) != self._manifest.embedding_dimension:
            raise ValueError("query dimension does not match the index manifest")
        if limit <= 0:
            return []
        hits: list[VectorHit] = []
        for record in self._records.values():
            similarity = cosine_similarity(vector, record.embedding)
            hits.append(
                VectorHit(
                    id=record.id,
                    document_id=record.document_id,
                    distance=1.0 - similarity,
                    similarity=similarity,
                    metadata=dict(record.metadata),
                )
            )
        hits.sort(key=lambda item: (-item.similarity, item.document_id, item.id))
        return hits[: min(limit, fetch_k, len(hits))]

    def delete_by_document(self, document_id: str) -> None:
        self._records = {
            key: value for key, value in self._records.items() if value.document_id != document_id
        }

    def delete_by_ids(self, chunk_ids: Sequence[str]) -> None:
        for chunk_id in chunk_ids:
            self._records.pop(str(chunk_id), None)

    def collection_manifest(self) -> IndexManifest:
        return self._manifest

    @property
    def count(self) -> int:
        return len(self._records)


class ChromaVectorStore:
    """Persistent Chroma adapter loaded only when the dependency is installed."""

    def __init__(
        self,
        path: str | Path,
        manifest: IndexManifest,
        *,
        client: Any | None = None,
    ) -> None:
        self._manifest = manifest
        try:
            if client is None:
                import chromadb  # type: ignore[import-not-found]

                client = chromadb.PersistentClient(path=str(Path(path)))
            self._collection = client.get_or_create_collection(
                name=manifest.collection_name,
                metadata={
                    "index_version": manifest.index_version,
                    "embedding_dimension": manifest.embedding_dimension,
                    "distance_metric": manifest.distance_metric,
                },
                configuration={"hnsw": {"space": manifest.distance_metric}},
            )
        except ImportError as exc:
            raise VectorStoreUnavailable(
                "ChromaDB is required for a staging or production vector profile"
            ) from exc
        except Exception as exc:
            raise VectorStoreUnavailable(f"could not open Chroma collection: {exc}") from exc

    def embed_query(self, query: str) -> tuple[float, ...]:
        return hash_embedding(query, self._manifest.embedding_dimension)

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        if not records:
            return
        for record in records:
            if len(record.embedding) != self._manifest.embedding_dimension:
                raise ValueError("embedding dimension does not match the index manifest")
        self._collection.upsert(
            ids=[record.id for record in records],
            embeddings=[list(record.embedding) for record in records],
            metadatas=[dict(record.metadata) for record in records],
        )

    def query(self, vector: Sequence[float], limit: int, fetch_k: int) -> list[VectorHit]:
        if len(vector) != self._manifest.embedding_dimension:
            raise ValueError("query dimension does not match the index manifest")
        result = self._collection.query(
            query_embeddings=[list(vector)],
            n_results=max(1, min(limit, fetch_k)),
            include=["metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        hits: list[VectorHit] = []
        for index, item_id in enumerate(ids):
            distance = float(distances[index]) if index < len(distances) else 0.0
            metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            similarity = 1.0 - distance if self._manifest.distance_metric == "cosine" else -distance
            hits.append(
                VectorHit(
                    id=str(item_id),
                    document_id=str(metadata.get("document_id", "")),
                    distance=distance,
                    similarity=similarity,
                    metadata=metadata,
                )
            )
        return hits

    def delete_by_document(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})

    def delete_by_ids(self, chunk_ids: Sequence[str]) -> None:
        if chunk_ids:
            self._collection.delete(ids=[str(item) for item in chunk_ids])

    def collection_manifest(self) -> IndexManifest:
        return self._manifest


__all__ = [
    "ChromaVectorStore",
    "IndexManifest",
    "InMemoryVectorStore",
    "VectorHit",
    "VectorRecord",
    "VectorStore",
    "VectorStoreUnavailable",
    "cosine_similarity",
    "hash_embedding",
]
