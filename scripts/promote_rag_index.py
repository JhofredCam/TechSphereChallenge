"""Promote or rollback a registered index without deleting prior versions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import Settings
from app.database import init_database
from app.services.index_manager import IndexManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote or rollback a RAG index.")
    parser.add_argument("--index-version", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--actor", default="local-operator")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    database = init_database(Settings(data_dir=args.data_dir))
    try:
        result = IndexManager(database, actor=args.actor).promote(
            args.index_version,
            reason=args.reason,
            status="rolled_back" if args.rollback else "active",
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
