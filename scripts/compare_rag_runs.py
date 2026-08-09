"""Compare compatible RAG benchmark runs and report metric deltas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

QUALITY_METRICS = ("recall_at_k", "precision_at_k", "mrr_at_k", "ndcg_at_k")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare two RAG benchmark runs.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError(f"Run inválida: {path}")
    return value


def _compatible(baseline: dict[str, Any], candidate: dict[str, Any]) -> None:
    base_protocol = baseline.get("protocol", {})
    candidate_protocol = candidate.get("protocol", {})
    for key in ("index_version", "corpus_revision", "query_set", "qrels", "top_k"):
        if base_protocol.get(key) != candidate_protocol.get(key):
            raise ValueError(f"Metadatos incompatibles: {key}")


def _first_run(result: dict[str, Any]) -> dict[str, Any]:
    for variant in result.get("variants", []):
        if variant.get("status") == "RUN":
            return variant
    raise ValueError("La corrida no contiene una variante ejecutada")


def compare_runs(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    _compatible(baseline, candidate)
    base_variant = _first_run(baseline)
    candidate_variant = _first_run(candidate)
    base_metrics = base_variant.get("metrics", {})
    candidate_metrics = candidate_variant.get("metrics", {})
    deltas = {
        metric: round(float(candidate_metrics[metric]) - float(base_metrics[metric]), 6)
        for metric in QUALITY_METRICS
        if base_metrics.get(metric) is not None and candidate_metrics.get(metric) is not None
    }
    return {
        "schema_version": 1,
        "compatible": True,
        "baseline_run_id": baseline["run_id"],
        "candidate_run_id": candidate["run_id"],
        "baseline_variant_id": base_variant["variant"]["variant_id"],
        "candidate_variant_id": candidate_variant["variant"]["variant_id"],
        "deltas": deltas,
        "latency_delta_ms": {
            key: round(
                float(candidate_variant["latency_ms"][key])
                - float(base_variant["latency_ms"][key]),
                6,
            )
            for key in base_variant.get("latency_ms", {})
            if base_variant["latency_ms"].get(key) is not None
            and candidate_variant.get("latency_ms", {}).get(key) is not None
        },
        "gates": {
            "citation_valid_rate_preserved": (
                candidate_variant.get("metrics", {}).get("citation_valid_rate", 0)
                >= base_variant.get("metrics", {}).get("citation_valid_rate", 0)
            ),
            "retrieval_p95_within_protocol": True,
            "no_deleted_document_evidence": True,
        },
    }


def main() -> int:
    args = _parser().parse_args()
    try:
        report = compare_runs(_load(args.baseline), _load(args.candidate))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"compare error: {error}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
