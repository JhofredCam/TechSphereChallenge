"""Run the deterministic, dependency-free RAG benchmark protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import unicodedata
from pathlib import Path
from statistics import mean
from typing import Any

LATENCY_STAGES = (
    "embedding_query",
    "vector_query",
    "fts5_query",
    "fusion_hydration",
    "validation",
    "retrieval_total",
)
TOKEN_RE = re.compile(r"[a-z0-9áéíóúüñ]+", re.IGNORECASE)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark retrieval variants reproducibly.")
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--queries", type=Path)
    parser.add_argument("--qrels", type=Path)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return None
    if value[0:1] in {'"', "'"} and value[-1:] == value[0]:
        return value[1:-1]
    if value.lower() in {"null", "none"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return value


def load_matrix(path: Path) -> dict[str, Any]:
    """Load JSON or the small YAML subset used by the checked-in matrix."""

    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("La matriz debe ser un objeto")
        return value
    except json.JSONDecodeError:
        pass

    root: dict[str, Any] = {}
    current_list: list[dict[str, Any]] | None = None
    current_item: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        line = raw_line.strip()
        if indent == 0:
            key, separator, raw_value = line.partition(":")
            if not separator:
                raise ValueError(f"Línea YAML inválida: {raw_line}")
            if raw_value.strip():
                root[key.strip()] = _scalar(raw_value)
                current_list = None
                current_item = None
            else:
                root[key.strip()] = []
                current_list = root[key.strip()]
                current_item = None
            continue
        if current_list is None:
            raise ValueError(f"Estructura YAML no soportada: {raw_line}")
        if line.startswith("- "):
            current_item = {}
            current_list.append(current_item)
            line = line[2:].strip()
        if current_item is None or ":" not in line:
            raise ValueError(f"Elemento YAML inválido: {raw_line}")
        key, _, raw_value = line.partition(":")
        current_item[key.strip()] = _scalar(raw_value)
    return root


def _resolve(path: Path, matrix_path: Path) -> Path:
    if path.is_absolute():
        return path
    candidates = [matrix_path.parent / path, matrix_path.parent.parent / path, Path.cwd() / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_jsonl(path: Path, required: tuple[str, ...]) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo requerido: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        row = json.loads(raw_line)
        if not isinstance(row, dict) or any(key not in row for key in required):
            raise ValueError(f"Fila inválida en {path}:{line_number}")
        forbidden = {"label_ground_truth", "password", "api_key", "transcript"}
        if forbidden.intersection(row):
            raise ValueError(f"Campo sensible en {path}:{line_number}")
        rows.append(row)
    if not rows:
        raise ValueError(f"Archivo JSONL vacío: {path}")
    return rows


def load_corpus(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows = load_jsonl(path, ("chunk_id", "text", "source_document_id"))
    seen: set[str] = set()
    for row in rows:
        chunk_id = str(row["chunk_id"])
        if chunk_id in seen:
            raise ValueError(f"chunk_id duplicado: {chunk_id}")
        seen.add(chunk_id)
    return rows


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return set(TOKEN_RE.findall(normalized))


def _hash_embedding(tokens: set[str], dimension: int = 32) -> list[float]:
    vector = [0.0] * dimension
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % dimension
        vector[index] += 1.0 if digest[2] % 2 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _rank(
    query: str, variant: dict[str, Any], corpus: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    query_vector = _hash_embedding(query_tokens)
    provider = str(variant.get("provider", ""))
    ranked: list[dict[str, Any]] = []
    for chunk in corpus:
        text_tokens = _tokens(str(chunk["text"]))
        lexical = len(query_tokens.intersection(text_tokens)) / max(len(query_tokens), 1)
        semantic = _cosine(query_vector, _hash_embedding(text_tokens))
        score = lexical if provider == "fts5" else max(0.0, semantic) * 0.7 + lexical * 0.3
        ranked.append({**chunk, "score": round(score, 8)})
    return sorted(ranked, key=lambda row: (-float(row["score"]), str(row["chunk_id"])))


def _ndcg(hits: list[str], relevance: dict[str, int], k: int) -> float:
    dcg = sum(
        (2 ** relevance.get(chunk_id, 0) - 1) / math.log2(index + 2)
        for index, chunk_id in enumerate(hits[:k])
    )
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum((2**value - 1) / math.log2(index + 2) for index, value in enumerate(ideal))
    return dcg / idcg if idcg else 1.0


def _average(values: list[float]) -> float | None:
    return round(mean(values), 6) if values else None


def evaluate_variant(
    variant: dict[str, Any],
    queries: list[dict[str, Any]],
    qrels: list[dict[str, Any]],
    corpus: list[dict[str, Any]],
    *,
    top_k: int,
    repetitions: int,
    index_version: str,
) -> dict[str, Any]:
    provider = str(variant.get("provider", ""))
    if provider not in {"fts5", "builtin_hash"}:
        return {
            "variant": variant,
            "status": "SKIPPED",
            "skip_reason": f"provider_unavailable:{provider}",
            "metrics": {},
            "latency_ms": {stage: None for stage in LATENCY_STAGES},
            "rows": [],
        }
    if not corpus:
        return {
            "variant": variant,
            "status": "SKIPPED",
            "skip_reason": "corpus_not_provided",
            "metrics": {},
            "latency_ms": {stage: None for stage in LATENCY_STAGES},
            "rows": [],
        }

    qrel_map: dict[str, dict[str, int]] = {}
    for qrel in qrels:
        qrel_map.setdefault(str(qrel["query_id"]), {})[str(qrel["chunk_id"])] = int(
            qrel["relevance"]
        )
    metric_values: dict[str, list[float]] = {
        "recall_at_k": [],
        "hit_rate_at_k": [],
        "precision_at_k": [],
        "mrr_at_k": [],
        "ndcg_at_k": [],
        "context_precision": [],
        "citation_valid_rate": [],
        "empty_rate": [],
    }
    latency_values = {stage: [] for stage in LATENCY_STAGES}
    rows: list[dict[str, Any]] = []
    for _ in range(max(repetitions, 1)):
        for query in queries:
            started = time.perf_counter()
            embedding_started = time.perf_counter()
            _hash_embedding(_tokens(str(query["query"])))
            embedding_ms = (time.perf_counter() - embedding_started) * 1000
            vector_started = time.perf_counter()
            ranked = _rank(str(query["query"]), variant, corpus)
            vector_ms = (time.perf_counter() - vector_started) * 1000
            fusion_started = time.perf_counter()
            hits = [str(item["chunk_id"]) for item in ranked[:top_k]]
            relevance = qrel_map.get(str(query["query_id"]), {})
            positives = {chunk_id for chunk_id, value in relevance.items() if value > 0}
            relevant_hits = [chunk_id for chunk_id in hits if chunk_id in positives]
            fusion_ms = (time.perf_counter() - fusion_started) * 1000
            validation_started = time.perf_counter()
            valid_ids = {str(item["chunk_id"]) for item in corpus}
            citation_valid = sum(chunk_id in valid_ids for chunk_id in hits) / max(len(hits), 1)
            validation_ms = (time.perf_counter() - validation_started) * 1000
            retrieval_ms = (time.perf_counter() - started) * 1000
            recall = len(relevant_hits) / len(positives) if positives else float(not hits)
            hit_rate = float(bool(relevant_hits)) if positives else float(not hits)
            precision = len(relevant_hits) / max(len(hits), 1)
            reciprocal_rank = next(
                (1 / (index + 1) for index, chunk_id in enumerate(hits) if chunk_id in positives),
                0.0,
            )
            context_precision = len(relevant_hits) / max(len(hits), 1)
            values = {
                "recall_at_k": recall,
                "hit_rate_at_k": hit_rate,
                "precision_at_k": precision,
                "mrr_at_k": reciprocal_rank,
                "ndcg_at_k": _ndcg(hits, relevance, top_k),
                "context_precision": context_precision,
                "citation_valid_rate": citation_valid,
                "empty_rate": float(not hits),
            }
            for name, value in values.items():
                metric_values[name].append(value)
            stage_values = {
                "embedding_query": embedding_ms,
                "vector_query": vector_ms if provider == "builtin_hash" else 0.0,
                "fts5_query": vector_ms if provider == "fts5" else 0.0,
                "fusion_hydration": fusion_ms,
                "validation": validation_ms,
                "retrieval_total": retrieval_ms,
            }
            for name, value in stage_values.items():
                latency_values[name].append(value)
            rows.append(
                {
                    "run_id": hashlib.sha256(
                        f"{variant['variant_id']}:{index_version}:{query['query_id']}".encode()
                    ).hexdigest()[:16],
                    "variant_id": variant["variant_id"],
                    "query_id": query["query_id"],
                    "index_version": index_version,
                    "chunking_version": variant.get("chunking"),
                    "embedding_model_name": variant.get("embedding_model_name"),
                    "embedding_model_revision": variant.get("embedding_model_revision"),
                    "provider": provider,
                    "k": top_k,
                    "score": ranked[0]["score"] if ranked else None,
                    "hit_ids": hits,
                    "latency_ms": stage_values,
                    "abstention_reason": "no_relevant_qrel" if not positives else None,
                }
            )
    return {
        "variant": variant,
        "status": "RUN",
        "metrics": {name: _average(values) for name, values in metric_values.items()},
        "latency_ms": {name: _average(values) for name, values in latency_values.items()},
        "rows": rows,
    }


def run_benchmark(
    matrix_path: Path,
    *,
    queries_path: Path | None = None,
    qrels_path: Path | None = None,
    corpus_path: Path | None = None,
    repetitions: int | None = None,
) -> dict[str, Any]:
    matrix = load_matrix(matrix_path)
    resolved_queries = _resolve(Path(queries_path or matrix["queries"]), matrix_path)
    resolved_qrels = _resolve(Path(qrels_path or matrix["qrels"]), matrix_path)
    queries = load_jsonl(resolved_queries, ("query_id", "query", "query_type"))
    qrels = load_jsonl(resolved_qrels, ("query_id", "chunk_id", "relevance"))
    if len({row["query_id"] for row in queries}) != len(queries):
        raise ValueError("query_id duplicado")
    for qrel in qrels:
        if int(qrel["relevance"]) not in {0, 1, 2}:
            raise ValueError("relevance debe ser 0, 1 o 2")
        if qrel["query_id"] not in {row["query_id"] for row in queries}:
            raise ValueError("qrel sin query")
    corpus = load_corpus(_resolve(corpus_path, matrix_path) if corpus_path else None)
    top_k = int(matrix.get("top_k", 5))
    repeats = int(repetitions or matrix.get("repetitions", 1))
    if top_k < 1 or repeats < 1:
        raise ValueError("top_k y repetitions deben ser positivos")
    index_version = str(matrix.get("index_version", "unknown"))
    variants = matrix.get("variants") or []
    if not isinstance(variants, list) or not variants:
        raise ValueError("La matriz debe contener variants")
    results = [
        evaluate_variant(
            variant,
            queries,
            qrels,
            corpus,
            top_k=top_k,
            repetitions=repeats,
            index_version=index_version,
        )
        for variant in variants
    ]
    for result in results:
        if result["status"] == "RUN" and set(result["latency_ms"]) != set(LATENCY_STAGES):
            raise ValueError(f"Variante sin latencias completas: {result['variant']['variant_id']}")
    return {
        "schema_version": 1,
        "run_id": hashlib.sha256(
            json.dumps(
                {"index_version": index_version, "queries": [row["query_id"] for row in queries]},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:16],
        "status": "OK",
        "protocol": {
            "index_version": index_version,
            "corpus_revision": matrix.get("corpus_revision", 0),
            "query_set": str(resolved_queries),
            "qrels": str(resolved_qrels),
            "top_k": top_k,
            "repetitions": repeats,
            "warmups": int(matrix.get("warmups", 0)),
            "latency_stages": list(LATENCY_STAGES),
        },
        "variants": results,
    }


def main() -> int:
    args = _parser().parse_args()
    try:
        result = run_benchmark(
            args.matrix,
            queries_path=args.queries,
            qrels_path=args.qrels,
            corpus_path=args.corpus,
            repetitions=args.repetitions,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"benchmark error: {error}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "run_id": result["run_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
