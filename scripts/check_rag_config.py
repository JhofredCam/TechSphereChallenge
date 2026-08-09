"""Validate and inspect the external RAG configuration without side effects."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from app.config import RagSettings, build_rag_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate RAG settings without opening a backend.")
    parser.add_argument("--profile", choices=("challenge-local", "staging", "production"))
    parser.add_argument("--show-effective", action="store_true")
    parser.add_argument("--redact-secrets", action="store_true", default=False)
    return parser


def validate(environ: dict[str, str] | None = None, *, profile: str | None = None) -> RagSettings:
    values = dict(os.environ if environ is None else environ)
    if profile:
        values["RAG_PROFILE"] = profile
    return build_rag_settings(values)


def main() -> int:
    args = _parser().parse_args()
    try:
        settings = validate(profile=args.profile)
    except ValueError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    payload: dict[str, Any] = {
        "valid": True,
        "profile": settings.profile,
        "backend": settings.backend,
        "index_version": settings.index_version,
        "index_name": settings.rag_index_name,
    }
    if args.show_effective:
        payload["effective"] = settings.effective_dict(redact_secrets=args.redact_secrets)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
