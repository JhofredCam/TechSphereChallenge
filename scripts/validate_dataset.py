"""Validate the four canonical local challenge workbooks.

This command is intentionally read-only. It opens each workbook through the existing
``app.dataset`` validator, which uses ``openpyxl`` read-only mode and never downloads or
rewrites dataset files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from app.config import PROJECT_ROOT
from app.dataset import validate_dataset as _validate_dataset
from app.schemas import DatasetValidationReport


def validation_report_to_dict(report: DatasetValidationReport) -> dict[str, Any]:
    """Return a JSON-serializable representation of a validation report."""

    return {
        "valid": report.valid,
        "errors": list(report.errors),
        "warnings": list(report.warnings),
        "tables": [
            {
                "path": table.path,
                "sheet_name": table.sheet_name,
                "headers": list(table.headers),
                "row_count": table.row_count,
                "errors": list(table.errors),
                "valid": table.valid,
            }
            for table in report.tables
        ],
    }


def format_validation_report(report: DatasetValidationReport) -> str:
    """Format the validation result for a human-readable CLI report."""

    lines = [f"Dataset validation: {'valid' if report.valid else 'invalid'}"]
    for table in report.tables:
        status = "ok" if table.valid else "error"
        lines.append(f"- {table.path}: {table.row_count} rows [{status}]")
        for error in table.errors:
            lines.append(f"  {error}")
    for error in report.errors:
        if not any(error in table.errors for table in report.tables):
            lines.append(f"- {error}")
    for warning in report.warnings:
        lines.append(f"- warning: {warning}")
    return "\n".join(lines)


def validate(dataset_dir: str | Path = PROJECT_ROOT / "dataset") -> DatasetValidationReport:
    """Validate all four canonical workbooks under ``dataset_dir``."""

    return _validate_dataset(dataset_dir)


validate_dataset = validate


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the four canonical XLSX files without modifying them."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=PROJECT_ROOT / "dataset",
        help="Directory containing the four canonical XLSX files (default: dataset).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print the report as JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the dataset validation command and return a process exit code."""

    args = _build_parser().parse_args(argv)
    report = validate(args.dataset_dir)
    if args.as_json:
        print(json.dumps(validation_report_to_dict(report), ensure_ascii=False, indent=2))
    else:
        print(format_validation_report(report))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "format_validation_report",
    "main",
    "validate",
    "validate_dataset",
    "validation_report_to_dict",
]
