from __future__ import annotations

import pytest

from app.config import MAX_UPLOAD_BYTES, Settings, get_settings


def test_settings_resolve_local_overrides_without_creating_directories(tmp_path):
    settings = Settings.from_env(
        {
            "APP_DATA_DIR": "local data",
            "APP_DATABASE_PATH": "state/app.sqlite3",
            "APP_UPLOADS_DIR": "uploaded documents",
            "APP_CHUNK_SIZE": "100",
            "APP_CHUNK_OVERLAP": "10",
            "APP_MAX_UPLOAD_BYTES": "1000",
        },
        project_root=tmp_path,
    )

    assert settings.data_dir == (tmp_path / "local data").resolve()
    assert settings.db_path == (tmp_path / "state/app.sqlite3").resolve()
    assert settings.documents_dir == (tmp_path / "uploaded documents").resolve()
    assert settings.chunk_size == 100
    assert settings.chunk_overlap == 10
    assert settings.max_upload_bytes == 1000
    assert not settings.data_dir.exists()

    direct = Settings(
        data_dir=tmp_path,
        database_path="custom.sqlite3",
        uploads_dir="custom uploads",
    )
    assert direct.db_path == (tmp_path / "custom.sqlite3").resolve()
    assert direct.documents_dir == (tmp_path / "custom uploads").resolve()


def test_settings_reject_invalid_integer_and_safety_limits(tmp_path):
    with pytest.raises(ValueError, match="APP_CHUNK_SIZE"):
        Settings.from_env({"APP_CHUNK_SIZE": "not-an-int"}, project_root=tmp_path)
    with pytest.raises(ValueError, match="chunk_size"):
        Settings(data_dir=tmp_path, chunk_size=0)
    with pytest.raises(ValueError, match="chunk_overlap"):
        Settings(data_dir=tmp_path, chunk_size=10, chunk_overlap=10)
    with pytest.raises(ValueError, match="max_upload_bytes"):
        Settings(data_dir=tmp_path, max_upload_bytes=MAX_UPLOAD_BYTES + 1)

    defaults = get_settings({"APP_DATA_DIR": str(tmp_path / "default-data")})
    assert defaults.data_dir == (tmp_path / "default-data").resolve()
