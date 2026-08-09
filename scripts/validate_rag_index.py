"""Validate one registered immutable index manifest before promotion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import Settings
from app.database import init_database
from app.services.index_manager import validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a versioned RAG index.")
    parser.add_argument("--index-version", required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    settings = Settings(data_dir=args.data_dir)
    database = init_database(settings)
    try:
        record = database.get_rag_index(args.index_version)
        if record is None:
            print(json.dumps({"valid": False, "reason": "index_not_found"}))
            return 2
        validate_manifest(record["manifest"])
        valid = record["status"] in {"validated", "shadow", "canary", "active"}
        if record["status"] == "building":
            database.upsert_rag_index(
                index_version=args.index_version,
                backend=str(record["backend"]),
                manifest=record["manifest"],
                status="validated",
                lag=int(record.get("lag") or 0),
            )
            record["status"] = "validated"
            valid = True
        payload = {
            "valid": valid,
            "index_version": args.index_version,
            "status": record["status"],
            "manifest": record["manifest"],
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0 if valid or not args.strict else 2
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
