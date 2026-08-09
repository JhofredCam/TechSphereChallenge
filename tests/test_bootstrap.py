from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.config import Settings
from app.database import init_database
from app.dataset import (
    CLINICAL_FILE,
    CONVERSATIONS_FILE,
    DEMOGRAPHIC_FILE,
    EXPECTED_HEADERS,
    TRAJECTORIES_FILE,
)
from app.services.documents import DocumentService
from scripts.bootstrap import bootstrap, format_bootstrap_report
from scripts.bootstrap import main as bootstrap_main


def _write_workbook(path: Path, headers: tuple[str, ...], row: dict[str, object]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "result"
    worksheet.append(list(headers))
    worksheet.append([row.get(header) for header in headers])
    workbook.save(path)


def _write_fixture_dataset(root: Path) -> dict[str, int]:
    patient_id = "pac-1"
    _write_workbook(
        root / CLINICAL_FILE,
        EXPECTED_HEADERS[CLINICAL_FILE],
        {
            "paciente_id": patient_id,
            "comorbilidades": "[]",
        },
    )
    _write_workbook(
        root / DEMOGRAPHIC_FILE,
        EXPECTED_HEADERS[DEMOGRAPHIC_FILE],
        {"paciente_id": patient_id, "adaptation_fields": "[]"},
    )
    _write_workbook(
        root / TRAJECTORIES_FILE,
        EXPECTED_HEADERS[TRAJECTORIES_FILE],
        {"trayectoria_id": "t-1", "paciente_id": patient_id},
    )
    _write_workbook(
        root / CONVERSATIONS_FILE,
        EXPECTED_HEADERS[CONVERSATIONS_FILE],
        {
            "caso_id": "caso_t-1",
            "paciente_id": patient_id,
            "capa": "capa1_limpia",
        },
    )
    return {name: 1 for name in EXPECTED_HEADERS}


def test_bootstrap_validates_without_rewriting_and_is_hash_idempotent(tmp_path):
    dataset_root = tmp_path / "dataset"
    textos_root = dataset_root / "textos" / "folder with spaces"
    textos_root.mkdir(parents=True)
    expected_counts = _write_fixture_dataset(dataset_root)

    source = textos_root / "guide with spaces.txt"
    source.write_text("Contenido clinico disponible.", encoding="utf-8")
    duplicate = textos_root / "duplicate.txt"
    duplicate.write_bytes(source.read_bytes())
    scanned = textos_root / "scanned source.txt"
    scanned.write_text("   \n", encoding="utf-8")
    canonical_before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in dataset_root.glob("*.xlsx")
    }

    settings = Settings(data_dir=tmp_path / "local data")
    first = bootstrap(
        dataset_root,
        textos_dir=Path("dataset/textos"),
        settings=settings,
        expected_counts=expected_counts,
    )

    assert first.valid is True
    assert first.discovered_count == 3
    assert first.document_count == 2
    assert first.ingested_count == 2
    assert first.skipped_count == 1
    assert first.available_count == 1
    assert first.needs_ocr_count == 1
    assert any("folder with spaces" in item.source_path for item in first.documents)
    assert any(item.needs_ocr for item in first.documents)
    assert settings.db_path.exists()
    assert canonical_before == {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in dataset_root.glob("*.xlsx")
    }

    second = bootstrap(
        dataset_root,
        settings=settings,
        expected_counts=expected_counts,
    )

    assert second.ingested_count == 0
    assert second.skipped_count == 3
    assert second.document_count == first.document_count
    assert second.corpus_revision == first.corpus_revision
    assert first.to_dict()["counts"]["unique_documents"] == 2
    assert "Bootstrap:" in format_bootstrap_report(first)


def test_bootstrap_rejects_roots_outside_dataset_and_reports_invalid_cli_input(tmp_path):
    dataset_root = tmp_path / "dataset"
    (dataset_root / "textos").mkdir(parents=True)
    settings = Settings(data_dir=tmp_path / "local")

    with pytest.raises(ValueError, match="must remain inside dataset_dir"):
        bootstrap(
            dataset_root,
            textos_dir=tmp_path / "outside-textos",
            settings=settings,
            expected_counts=None,
        )
    expected_counts = _write_fixture_dataset(dataset_root)
    with pytest.raises(ValueError, match="pass settings or data_dir"):
        bootstrap(
            dataset_root,
            settings=settings,
            data_dir=tmp_path / "other",
            expected_counts=expected_counts,
        )

    assert bootstrap_main(
        ["--dataset-dir", str(dataset_root), "--data-dir", str(tmp_path / "cli-data"), "--json"]
    ) == 1


def test_bootstrap_audits_failed_storage_cleanup_after_forgetting_document(tmp_path, monkeypatch):
    dataset_root = tmp_path / "dataset"
    textos_root = dataset_root / "textos"
    textos_root.mkdir(parents=True)
    expected_counts = _write_fixture_dataset(dataset_root)
    source = textos_root / "guide with spaces.txt"
    source.write_text("Contenido clinico disponible.", encoding="utf-8")
    settings = Settings(data_dir=tmp_path / "local data")

    report = bootstrap(dataset_root, settings=settings, expected_counts=expected_counts)
    document_id = next(item.document_id for item in report.documents if item.document_id)
    database = init_database(settings)
    documents = DocumentService(database, settings)
    stored_path = Path(documents.get(document_id).stored_path)
    original_unlink = Path.unlink

    def fail_stored_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path == stored_path:
            raise PermissionError("locked by test")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_stored_unlink)

    assert documents.delete(document_id) is True
    assert documents.get(document_id) is None
    audit = database.execute(
        "SELECT action, details_json FROM audit "
        "WHERE entity_id = ? ORDER BY id DESC LIMIT 1",
        (document_id,),
    ).fetchone()
    assert audit["action"] == "delete_storage_error"
    assert "locked by test" in audit["details_json"]
