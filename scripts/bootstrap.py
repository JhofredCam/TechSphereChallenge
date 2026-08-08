"""Initialize local state and ingest the bundled clinical corpus.

The orchestration in this module deliberately stays at the tooling boundary. Dataset
validation, SQLite initialization, document lifecycle, content hashing, and extraction
remain owned by the existing ``app`` modules. No provider client or network operation is
needed to run this command.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.config import PROJECT_ROOT, Settings, get_settings
from app.database import init_database
from app.dataset import (
    EXPECTED_ROW_COUNTS,
    DatasetValidationError,
    validate_dataset,
)
from app.schemas import DatasetValidationReport, DocumentStatus
from app.services.documents import DocumentService, safe_storage_filename
from app.services.ingestion import (
    document_id_for_bytes,
    guess_mime_type,
    iter_supported_files,
)

from .validate_dataset import format_validation_report, validation_report_to_dict


@dataclass(frozen=True, slots=True)
class BootstrapDocumentReport:
    """Result for one source path, including duplicate paths for observability."""

    source_path: str
    document_id: str | None
    filename: str
    status: DocumentStatus | str
    action: str
    needs_ocr: bool
    error: str | None = None

    @property
    def status_value(self) -> str:
        return self.status.value if isinstance(self.status, DocumentStatus) else str(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "document_id": self.document_id,
            "filename": self.filename,
            "status": self.status_value,
            "action": self.action,
            "needs_ocr": self.needs_ocr,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class BootstrapReport:
    """Complete result of one bootstrap run."""

    dataset_path: str
    textos_path: str
    data_dir: str
    database_path: str
    validation: DatasetValidationReport
    documents: tuple[BootstrapDocumentReport, ...]
    corpus_revision: int

    @property
    def valid(self) -> bool:
        return self.validation.valid and not self.error_count

    @property
    def discovered_count(self) -> int:
        return len(self.documents)

    @property
    def file_count(self) -> int:
        return self.discovered_count

    @property
    def unique_document_ids(self) -> frozenset[str]:
        return frozenset(
            document.document_id for document in self.documents if document.document_id is not None
        )

    @property
    def document_count(self) -> int:
        return len(self.unique_document_ids)

    @property
    def ingested_count(self) -> int:
        return sum(document.action == "ingested" for document in self.documents)

    @property
    def skipped_count(self) -> int:
        return sum(document.action == "skipped" for document in self.documents)

    @property
    def reprocessed_count(self) -> int:
        return sum(document.action == "reprocessed" for document in self.documents)

    @property
    def processed_count(self) -> int:
        return self.status_counts.get(DocumentStatus.AVAILABLE.value, 0) + self.status_counts.get(
            DocumentStatus.NEEDS_OCR.value, 0
        )

    @property
    def status_counts(self) -> dict[str, int]:
        """Count final statuses once per content hash, not once per duplicate path."""

        counts: dict[str, int] = {}
        seen_ids: set[str] = set()
        for document in self.documents:
            if document.document_id is not None:
                if document.document_id in seen_ids:
                    continue
                seen_ids.add(document.document_id)
            status = document.status_value
            counts[status] = counts.get(status, 0) + 1
        return counts

    @property
    def document_status_counts(self) -> dict[str, int]:
        return self.status_counts

    @property
    def available_count(self) -> int:
        return self.status_counts.get(DocumentStatus.AVAILABLE.value, 0)

    @property
    def needs_ocr_count(self) -> int:
        return self.status_counts.get(DocumentStatus.NEEDS_OCR.value, 0)

    @property
    def error_count(self) -> int:
        return self.status_counts.get(DocumentStatus.ERROR.value, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_path": self.dataset_path,
            "textos_path": self.textos_path,
            "data_dir": self.data_dir,
            "database_path": self.database_path,
            "dataset": validation_report_to_dict(self.validation),
            "counts": {
                "discovered_files": self.discovered_count,
                "unique_documents": self.document_count,
                "ingested": self.ingested_count,
                "skipped_by_hash": self.skipped_count,
                "reprocessed": self.reprocessed_count,
                "processed": self.processed_count,
            },
            "status_counts": self.status_counts,
            "corpus_revision": self.corpus_revision,
            "documents": [document.to_dict() for document in self.documents],
        }


def _resolve_path(value: str | Path, *, base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _resolve_source_roots(
    dataset_dir: str | Path | None,
    textos_dir: str | Path | None,
) -> tuple[Path, Path]:
    dataset_root = _resolve_path(dataset_dir or PROJECT_ROOT / "dataset", base=PROJECT_ROOT)
    if textos_dir is None:
        textos_root = _resolve_path(dataset_root / "textos", base=PROJECT_ROOT)
    else:
        relative_textos = Path(textos_dir).expanduser()
        textos_base = (
            dataset_root.parent
            if not relative_textos.is_absolute()
            and relative_textos.parts
            and relative_textos.parts[0].casefold() == dataset_root.name.casefold()
            else dataset_root
        )
        textos_root = _resolve_path(relative_textos, base=textos_base)
    try:
        relative_textos = textos_root.relative_to(dataset_root)
    except ValueError as exc:
        raise ValueError("textos_dir must remain inside dataset_dir") from exc
    if not relative_textos.parts or relative_textos.parts[0].casefold() != "textos":
        raise ValueError("bootstrap may ingest only dataset/textos")
    if not textos_root.is_dir():
        raise FileNotFoundError(textos_root)
    return dataset_root, textos_root


def _settings_for_bootstrap(
    settings: Settings | None,
    data_dir: str | Path | None,
) -> Settings:
    if settings is not None and data_dir is not None:
        raise ValueError("pass settings or data_dir, not both")
    if settings is not None:
        return settings
    if data_dir is not None:
        return Settings(data_dir=Path(data_dir))
    return get_settings()


def _status_for_error(error: Exception) -> tuple[DocumentStatus, str]:
    message = str(error).strip() or error.__class__.__name__
    return DocumentStatus.ERROR, message[:1000]


def _storage_filename(source_path: Path, settings: Settings, document_id: str) -> str:
    """Delegate bootstrap names to the same policy used by HTTP uploads."""

    return safe_storage_filename(
        source_path.name,
        storage_directory=settings.documents_dir / document_id,
        document_id=document_id,
    )


def bootstrap(
    dataset_dir: str | Path | None = None,
    *,
    textos_dir: str | Path | None = None,
    settings: Settings | None = None,
    data_dir: str | Path | None = None,
    expected_counts: Mapping[str, int | None] | None = EXPECTED_ROW_COUNTS,
) -> BootstrapReport:
    """Validate local workbooks, initialize SQLite, and ingest ``dataset/textos``.

    The default row counts are the canonical challenge counts. ``expected_counts`` is
    injectable for small local fixtures, while the default always validates the real
    four-workbook contract. Existing documents are looked up by SHA-256 before upload;
    the existing document service then avoids reprocessing available content.
    """

    dataset_root, textos_root = _resolve_source_roots(dataset_dir, textos_dir)
    validation = validate_dataset(dataset_root, expected_counts=expected_counts)
    if not validation.valid:
        raise DatasetValidationError(validation)

    configured_settings = _settings_for_bootstrap(settings, data_dir)
    configured_settings.ensure_directories()
    reports: list[BootstrapDocumentReport] = []
    with init_database(configured_settings) as database:
        documents = DocumentService(database, configured_settings)
        for source_path in iter_supported_files(textos_root):
            source_path = source_path.resolve()
            digest: str | None = None
            existing = None
            try:
                content = source_path.read_bytes()
                digest = document_id_for_bytes(content)
                existing = database.get_document_by_hash(digest)
                action = "ingested" if existing is None else "skipped"
                if existing is not None and existing.status in {
                    DocumentStatus.PROCESSING,
                    DocumentStatus.ERROR,
                }:
                    action = "reprocessed"
                    if not Path(existing.stored_path).is_file():
                        documents.delete(existing.id)
                        existing = None
                        action = "ingested"
                record = documents.upload(
                    content,
                    _storage_filename(source_path, configured_settings, digest),
                    mime_type=guess_mime_type(source_path),
                    process=True,
                )
                status = record.status
                error = record.error
                reports.append(
                    BootstrapDocumentReport(
                        source_path=str(source_path),
                        document_id=record.id,
                        filename=record.filename,
                        status=status,
                        action=action,
                        needs_ocr=status == DocumentStatus.NEEDS_OCR,
                        error=error,
                    )
                )
            except Exception as error:
                status, message = _status_for_error(error)
                reports.append(
                    BootstrapDocumentReport(
                        source_path=str(source_path),
                        document_id=digest,
                        filename=source_path.name,
                        status=status,
                        action="error",
                        needs_ocr=False,
                        error=message,
                    )
                )
        corpus_revision = documents.corpus_revision
        database_path = str(configured_settings.db_path)

    return BootstrapReport(
        dataset_path=str(dataset_root),
        textos_path=str(textos_root),
        data_dir=str(configured_settings.data_dir),
        database_path=database_path,
        validation=validation,
        documents=tuple(reports),
        corpus_revision=corpus_revision,
    )


run_bootstrap = bootstrap


def format_bootstrap_report(report: BootstrapReport) -> str:
    """Format validation, ingestion counts, and per-source statuses for the CLI."""

    lines = [format_validation_report(report.validation)]
    lines.extend(
        [
            "",
            "Bootstrap:",
            f"- discovered files: {report.discovered_count}",
            f"- unique documents: {report.document_count}",
            f"- ingested: {report.ingested_count}",
            f"- skipped by content hash: {report.skipped_count}",
            f"- reprocessed: {report.reprocessed_count}",
            f"- corpus revision: {report.corpus_revision}",
            f"- status counts: {json.dumps(report.status_counts, sort_keys=True)}",
        ]
    )
    for document in report.documents:
        lines.append(
            f"- {document.source_path}: {document.status_value} "
            f"({document.action}, sha256={document.document_id or 'unavailable'})"
        )
        if document.error:
            lines.append(f"  error: {document.error}")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize local data and ingest dataset/textos without network access."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=PROJECT_ROOT / "dataset",
        help="Directory containing the canonical XLSX files (default: dataset).",
    )
    parser.add_argument(
        "--textos-dir",
        type=Path,
        default=None,
        help="Optional dataset/textos directory; it must remain under --dataset-dir.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Local application data directory (otherwise APP_DATA_DIR or data).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print the complete report as JSON.",
    )
    return parser


def _configure_stdout() -> None:
    """Keep reports printable for corpus filenames outside the Windows ANSI code page."""

    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="strict")


def main(argv: Sequence[str] | None = None) -> int:
    """Run bootstrap and return a process exit code."""

    _configure_stdout()
    args = _build_parser().parse_args(argv)
    try:
        report = bootstrap(
            args.dataset_dir,
            textos_dir=args.textos_dir,
            data_dir=args.data_dir,
        )
    except DatasetValidationError as error:
        if args.as_json:
            print(
                json.dumps(
                    {"valid": False, "dataset": validation_report_to_dict(error.report)},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(format_validation_report(error.report))
        return 1
    except (FileNotFoundError, ValueError) as error:
        print(f"Bootstrap error: {error}")
        return 1

    if args.as_json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_bootstrap_report(report))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BootstrapDocumentReport",
    "BootstrapReport",
    "bootstrap",
    "format_bootstrap_report",
    "main",
    "run_bootstrap",
]
