"""Check tracing privacy flags without making a network request by default."""

from __future__ import annotations

import argparse
import json
import os
import sys

from app.config import Settings


def check(environ: dict[str, str] | None = None) -> dict[str, object]:
    values = dict(os.environ if environ is None else environ)
    settings = Settings.from_env(values)
    tracing = settings.rag.langchain_tracing
    capture = settings.rag.langsmith_capture_content
    redacted = settings.rag.langsmith_redact_pii
    if settings.rag.profile in {"staging", "production"} and capture and not redacted:
        raise ValueError("staging/production require LANGSMITH_REDACT_PII=true")
    if tracing and capture and not redacted:
        raise ValueError("content capture requires redaction")
    return {
        "profile": settings.rag.profile,
        "langsmith_enabled": tracing,
        "capture_content": capture,
        "redact_pii": redacted,
        "offline": True,
        "exporter": "langsmith-optional" if tracing else "noop",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local observability privacy configuration.")
    parser.add_argument("--redacted", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--project")
    args = parser.parse_args()
    if args.online:
        print("online no se ejecuta en CI; use un entorno controlado", file=sys.stderr)
        return 2
    try:
        print(json.dumps(check(), ensure_ascii=False))
    except ValueError as error:
        print(f"observability error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
