"""Deterministic lexical retrieval with source and corpus-revision traceability."""

from __future__ import annotations

import re

from ..config import Settings
from ..database import Database
from ..schemas import SearchResult
from .ingestion import normalize_for_search
from .vector_store import VectorStore

# Question words and function words do not provide enough evidence to ground a
# clinical answer.  Keeping this list local to retrieval makes the guard
# deterministic and avoids treating a generic "consulte a su medico" chunk as
# relevant to every question.
_RELEVANCE_STOPWORDS = frozenset(
    {
        "a",
        "al",
        "algo",
        "alguna",
        "alguno",
        "algunas",
        "algunos",
        "ante",
        "antes",
        "aqui",
        "asi",
        "cada",
        "como",
        "con",
        "contra",
        "cual",
        "cuales",
        "cuando",
        "de",
        "del",
        "desde",
        "donde",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "es",
        "esa",
        "ese",
        "eso",
        "esta",
        "este",
        "estos",
        "hay",
        "hace",
        "hacia",
        "hasta",
        "la",
        "las",
        "lo",
        "los",
        "me",
        "mi",
        "mis",
        "muy",
        "necesito",
        "no",
        "o",
        "para",
        "por",
        "puede",
        "puedo",
        "podria",
        "que",
        "quiero",
        "se",
        "sin",
        "sobre",
        "son",
        "su",
        "sus",
        "tambien",
        "te",
        "tengo",
        "tener",
        "tiene",
        "tienen",
        "un",
        "una",
        "uno",
        "unos",
        "y",
        "ya",
        "yo",
        "debo",
        "deber",
        "deberia",
        "hacer",
        "hago",
        "tomar",
        "tome",
        "toma",
    }
)


def _relevance_tokens(value: str) -> tuple[str, ...]:
    normalized = normalize_for_search(str(value or ""))
    tokens = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
    return tuple(
        dict.fromkeys(
            token
            for token in tokens
            if len(token) > 2 and token not in _RELEVANCE_STOPWORDS
        )
    )


def _related_token(left: str, right: str) -> bool:
    if left == right:
        return True
    if min(len(left), len(right)) < 5:
        return False
    prefix_length = 0
    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break
        prefix_length += 1
    return prefix_length >= max(5, min(len(left), len(right)) - 2)


def relevance_score(query: str, text: str) -> int:
    """Count distinct query concepts also present in a retrieved chunk."""

    query_tokens = _relevance_tokens(query)
    source_tokens = _relevance_tokens(text)
    return sum(
        any(_related_token(query_token, source_token) for source_token in source_tokens)
        for query_token in query_tokens
    )


def is_relevant(query: str, text: str) -> bool:
    """Require concrete lexical evidence before exposing a chunk to the agent.

    A one-concept query may be answered from a chunk containing that concept.
    Natural-language clinical questions with multiple concepts must match at
    least two; this prevents a generic chunk that happens to contain one broad
    word from becoming a grounded answer.
    """

    query_tokens = _relevance_tokens(query)
    if not query_tokens or not _relevance_tokens(text):
        return False
    required_matches = 1 if len(query_tokens) == 1 else 2
    return relevance_score(query, text) >= required_matches


def _fts_query(value: str) -> str:
    normalized = normalize_for_search(value)
    tokens = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
    # Quote every token so punctuation in patient language cannot become FTS syntax.
    return " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)


def search(
    database: Database,
    query: str,
    *,
    limit: int = 5,
) -> list[SearchResult]:
    """Search only currently published chunks and return auditable citations."""

    if limit <= 0:
        return []
    match_query = _fts_query(query)
    if not match_query:
        return []
    revision_before = database.get_corpus_revision()
    rows = database.execute(
        """
        SELECT
            chunks_fts.chunk_id,
            chunks_fts.document_id,
            chunks_fts.page_number,
            chunks.chunk_index,
            chunks.text,
            documents.filename,
            bm25(chunks_fts) AS rank
        FROM chunks_fts
        JOIN chunks ON chunks.id = chunks_fts.chunk_id
        JOIN documents ON documents.id = chunks.document_id
        WHERE chunks_fts MATCH ?
          AND documents.status = ?
          AND documents.enabled = 1
        ORDER BY rank ASC, chunks.document_id ASC,
                 chunks.page_number ASC, chunks.chunk_index ASC
        LIMIT ?
        """,
        (match_query, "available", max(limit, limit * 4)),
    ).fetchall()
    revision = database.get_corpus_revision()
    if revision != revision_before:
        # A corpus mutation raced the read. Returning no evidence is safer than
        # persisting a citation whose revision no longer describes the result.
        return []
    results: list[SearchResult] = []
    for row in rows:
        text = str(row["text"])
        if not is_relevant(query, text):
            continue
        rank = float(row["rank"])
        results.append(
            SearchResult(
                document_id=str(row["document_id"]),
                filename=str(row["filename"]),
                page_number=int(row["page_number"]),
                chunk_id=str(row["chunk_id"]),
                text=text,
                score=-rank,
                citation=f"{row['filename']} (p. {row['page_number']})",
                corpus_revision=revision,
                chunk_index=int(row["chunk_index"]),
            )
        )
        if len(results) >= limit:
            break
    return results


class RagService:
    """Object-oriented facade used by API and call services."""

    def __init__(
        self,
        database: Database,
        *,
        vector_store: VectorStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.database = database
        self.vector_store = vector_store
        self.settings = settings

    def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        if self.vector_store is not None:
            try:
                return self.semantic_search(query, limit=limit)
            except Exception:
                if self.settings is not None and not self.settings.rag.fallback_to_fts5:
                    raise
        return search(self.database, query, limit=limit)

    def retrieve(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        return self.search(query, limit=limit)

    def context(self, query: str, *, limit: int = 5) -> str:
        """Build a bounded, citation-preserving context block for a later model adapter."""

        results = self.search(query, limit=limit)
        return "\n\n".join(
            f"[{result.citation}]\n{result.text}" for result in results
        )

    def semantic_search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        """Query a derived vector index and hydrate every hit from SQLite."""

        if self.vector_store is None:
            return []
        if limit <= 0:
            return []
        embed_query = getattr(self.vector_store, "embed_query", None)
        if not callable(embed_query):
            raise ValueError("vector store does not provide an embedding query adapter")
        vector = embed_query(query)
        fetch_k = max(limit, getattr(getattr(self.settings, "rag", None), "vector_fetch_k", limit))
        hits = self.vector_store.query(vector, limit=limit, fetch_k=fetch_k)
        revision_before = self.database.get_corpus_revision()
        manifest = self.vector_store.collection_manifest()
        if manifest.corpus_revision and manifest.corpus_revision != revision_before:
            return []
        threshold = getattr(getattr(self.settings, "rag", None), "similarity_threshold", None)
        results: list[SearchResult] = []
        for hit in hits:
            if threshold is not None and hit.similarity < threshold:
                continue
            row = self.database.get_eligible_chunk(hit.id)
            if row is None:
                continue
            metadata_revision = hit.metadata.get("corpus_revision")
            if metadata_revision not in (None, "") and int(metadata_revision) != revision_before:
                continue
            results.append(
                SearchResult(
                    document_id=str(row["document_id"]),
                    filename=str(row["filename"]),
                    page_number=int(row["page_number"]),
                    chunk_id=str(row["id"]),
                    text=str(row["text"]),
                    score=float(hit.similarity),
                    citation=f"{row['filename']} (p. {row['page_number']})",
                    corpus_revision=revision_before,
                    chunk_index=int(row["chunk_index"]),
                )
            )
            if len(results) >= limit:
                break
        if self.database.get_corpus_revision() != revision_before:
            return []
        results.sort(
            key=lambda item: (
                -item.score,
                item.document_id,
                item.page_number,
                item.chunk_index or 0,
                item.chunk_id,
            )
        )
        return results


RAGService = RagService
search_corpus = search


__all__ = [
    "RAGService",
    "RagService",
    "is_relevant",
    "relevance_score",
    "search",
    "search_corpus",
]
