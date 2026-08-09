from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.benchmark_rag import LATENCY_STAGES, load_matrix, run_benchmark
from scripts.compare_rag_runs import compare_runs
from scripts.prepare_rag_eval import prepare_seed

ROOT = Path(__file__).resolve().parents[1]


def test_checked_in_matrix_has_baseline_three_embedding_options_and_fixed_protocol():
    matrix = load_matrix(ROOT / "configs" / "rag_benchmark.yaml")
    variants = matrix["variants"]
    assert len(variants) >= 4
    assert any(item["provider"] == "fts5" for item in variants)
    assert len({item["embedding_model_name"] for item in variants}) >= 4
    assert matrix["top_k"] == 5
    assert matrix["repetitions"] == 5


def test_prepare_seed_separates_queries_and_qrels_without_sensitive_fields(tmp_path):
    queries, qrels = prepare_seed(ROOT / "dataset" / "textos")
    assert queries
    assert qrels
    assert {row["query_id"] for row in qrels} <= {row["query_id"] for row in queries}
    rendered = json.dumps(queries + qrels, ensure_ascii=False).lower()
    assert "label_ground_truth" not in rendered
    assert "password" not in rendered


def test_benchmark_skips_unavailable_providers_without_fabricating_scores(tmp_path):
    output = tmp_path / "run.json"
    result = run_benchmark(ROOT / "configs" / "rag_benchmark.yaml")
    output.write_text(json.dumps(result), encoding="utf-8")
    skipped = [item for item in result["variants"] if item["status"] == "SKIPPED"]
    assert skipped
    assert all(item["metrics"] == {} for item in skipped)
    assert all(set(item["latency_ms"]) == set(LATENCY_STAGES) for item in skipped)


def test_benchmark_reports_stage_latencies_for_a_deterministic_corpus(tmp_path):
    corpus = tmp_path / "chunks.jsonl"
    corpus.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "chunk_id": "doc-a::chunk-0000",
                        "text": "dolor fiebre herida cirugía",
                        "source_document_id": "doc-a",
                        "page": 1,
                    }
                ),
                json.dumps(
                    {
                        "chunk_id": "doc-b::chunk-0000",
                        "text": "horario de biblioteca y transporte",
                        "source_document_id": "doc-b",
                        "page": 1,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    queries = tmp_path / "queries.jsonl"
    queries.write_text(
        json.dumps(
            {
                "query_id": "q1",
                "query": "fiebre herida",
                "query_type": "literal",
                "source_document_id": "doc-a",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    qrels = tmp_path / "qrels.jsonl"
    qrels.write_text(
        json.dumps(
            {
                "query_id": "q1",
                "chunk_id": "doc-a::chunk-0000",
                "relevance": 2,
                "source_document_id": "doc-a",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    matrix = tmp_path / "matrix.yaml"
    matrix.write_text(
        "\n".join(
            [
                "version: 1",
                "index_version: test-v1",
                "corpus_revision: 0",
                "top_k: 1",
                "repetitions: 1",
                f"queries: {queries}",
                f"qrels: {qrels}",
                "variants:",
                "  - variant_id: test-fts",
                "    chunking: c0",
                "    provider: fts5",
                "    embedding_model_name: none",
                "    embedding_model_revision: none",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    result = run_benchmark(matrix, corpus_path=corpus)
    run = result["variants"][0]
    assert run["status"] == "RUN"
    assert set(run["latency_ms"]) == set(LATENCY_STAGES)
    assert run["metrics"]["recall_at_k"] == 1.0
    assert '"text":' not in json.dumps(result).lower()


def test_compare_rejects_incompatible_index_versions():
    base = {"schema_version": 1, "run_id": "a", "protocol": {"index_version": "v1"}}
    candidate = {"schema_version": 1, "run_id": "b", "protocol": {"index_version": "v2"}}
    with pytest.raises(ValueError, match="index_version"):
        compare_runs(base, candidate)
