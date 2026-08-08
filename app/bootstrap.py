"""Module entry point for local bootstrap.

``scripts.bootstrap`` owns the orchestration and report contracts. This module is only a
thin convenience wrapper so the same command can be run as ``python -m app.bootstrap``.
"""

from scripts.bootstrap import (
    BootstrapDocumentReport,
    BootstrapReport,
    bootstrap,
    format_bootstrap_report,
    main,
    run_bootstrap,
)

__all__ = [
    "BootstrapDocumentReport",
    "BootstrapReport",
    "bootstrap",
    "format_bootstrap_report",
    "main",
    "run_bootstrap",
]


if __name__ == "__main__":
    raise SystemExit(main())
