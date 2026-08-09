"""Report SQLite/vector-index divergence without changing canonical content."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import Settings
from app.database import init_database


def reconcile(data_dir: str | Path, index_version: str | None = None) -> dict[str, object]:
    settings = Settings(data_dir=Path(data_dir))
    database = init_database(settings)
    try:
        indexes = database.list_rag_indexes()
        selected = (
            next((item for item in indexes if item["index_version"] == index_version), None)
            if index_version
            else (indexes[0] if indexes else None)
        )
        eligible_chunks = database.list_eligible_chunks()
        return {
            "valid": selected is not None or index_version is None,
            "index_version": index_version,
            "selected": selected,
            "corpus_revision": database.get_corpus_revision(),
            "eligible_chunk_count": len(eligible_chunks),
            "sqlite_authority": True,
            "repair_required": selected is None and index_version is not None,
        }
    finally:
        database.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile SQLite and the active RAG index.")
    parser.add_argument("--index-version")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = reconcile(args.data_dir, args.index_version)
    report["dry_run"] = args.dry_run
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str))
    return 0 if bool(report["valid"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
