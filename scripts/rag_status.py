"""Print safe operational status for versioned RAG indexes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import Settings
from app.database import init_database
from app.services.index_manager import IndexManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Show safe RAG operation status.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--redact-secrets", action="store_true")
    args = parser.parse_args()
    database = init_database(Settings(data_dir=args.data_dir))
    try:
        payload = IndexManager(database).status()
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
