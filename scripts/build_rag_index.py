"""Create a reproducible, redacted RAG manifest for the configured local profile.

This first migration step deliberately creates metadata only. Chroma backfill and
vector writes belong to Spec 14; the challenge-local FTS5 path remains untouched.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.config import PROJECT_ROOT, Settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a versioned RAG manifest.")
    parser.add_argument("--profile", choices=("challenge-local", "staging", "production"))
    parser.add_argument("--index-version")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def build_manifest(
    *,
    environ: dict[str, str] | None = None,
    profile: str | None = None,
    index_version: str | None = None,
    data_dir: Path | None = None,
) -> tuple[dict[str, object], Path]:
    values = dict(os.environ if environ is None else environ)
    if profile:
        values["RAG_PROFILE"] = profile
    if index_version:
        values["RAG_INDEX_VERSION"] = index_version
    if data_dir is not None:
        values["APP_DATA_DIR"] = str(data_dir)
    settings = Settings.from_env(values, project_root=PROJECT_ROOT)
    settings.ensure_directories()
    manifest_dir = settings.data_dir / "rag" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{settings.rag.index_version}.json"
    manifest: dict[str, object] = {
        "manifest_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": settings.rag.profile,
        "index_version": settings.rag.index_version,
        "index_name": settings.rag.rag_index_name,
        "backend": settings.rag.backend,
        "vector_store_type": settings.rag.vector_store_type,
        "corpus_revision": 0,
        "config": settings.rag.effective_dict(redact_secrets=True),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest, manifest_path


def main() -> int:
    args = _parser().parse_args()
    manifest, path = build_manifest(
        profile=args.profile,
        index_version=args.index_version,
        data_dir=args.data_dir,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {"manifest": str(path), "index_version": manifest["index_version"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
