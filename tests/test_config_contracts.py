from __future__ import annotations

import os

import pytest

from app.config import MAX_UPLOAD_BYTES, Settings, build_rag_settings, get_settings


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


def test_local_env_loading_is_opt_in_and_process_variables_win(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "# local-only provider settings\n"
        "export GROQ_API_KEY='file-key' # do not log this\n"
        'GROQ_MODEL="file-model"\n'
        "INVALID LINE\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    isolated = Settings.from_env(project_root=tmp_path)
    assert isolated.groq_api_key is None

    loaded = Settings.from_env(project_root=tmp_path, load_dotenv=True)
    assert loaded.groq_api_key == "file-key"
    assert loaded.groq_model == "file-model"
    assert os.getenv("GROQ_API_KEY") is None

    monkeypatch.setenv("GROQ_API_KEY", "process-key")
    process_wins = Settings.from_env(project_root=tmp_path, load_dotenv=True)
    assert process_wins.groq_api_key == "process-key"


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


def test_rag_settings_keep_local_profile_offline_and_redact_secrets(tmp_path):
    settings = build_rag_settings(
        {
            "APP_DATA_DIR": "rag-data",
            "EMBEDDING_ENDPOINT": "https://embedding.example/v1",
            "VECTOR_STORE_AUTH_TOKEN": "secret-token",
        },
        project_root=tmp_path,
    )

    assert settings.profile == "challenge-local"
    assert settings.backend == "fts5"
    assert settings.vector_store_type == "fts5"
    assert settings.embedding_provider == "none"
    assert settings.vector_store_path == (tmp_path / "rag-data/chroma").resolve()
    assert not settings.vector_store_path.exists()
    effective = settings.effective_dict(redact_secrets=True)
    assert effective["vector_store_auth_token"] == "[redacted]"
    assert effective["embedding_endpoint"] == "[redacted]"


def test_rag_settings_map_legacy_chunk_names_and_reject_inconsistent_values(tmp_path):
    settings = build_rag_settings(
        {"APP_CHUNK_SIZE": "900", "APP_CHUNK_OVERLAP": "100"},
        project_root=tmp_path,
    )
    assert (settings.chunk_size, settings.chunk_overlap) == (900, 100)

    with pytest.raises(ValueError, match="CHUNK_OVERLAP"):
        build_rag_settings(
            {"CHUNK_SIZE": "100", "CHUNK_OVERLAP": "100"},
            project_root=tmp_path,
        )


def test_rag_staging_requires_preloaded_embedding_provider(tmp_path):
    with pytest.raises(ValueError, match="embedding provider"):
        build_rag_settings({"RAG_PROFILE": "staging"}, project_root=tmp_path)

    settings = build_rag_settings(
        {
            "RAG_PROFILE": "staging",
            "EMBEDDING_PROVIDER": "fastembed",
            "EMBEDDING_MODEL_REVISION": "sha256:test",
        },
        project_root=tmp_path,
    )
    assert settings.profile == "staging"
    assert settings.embedding_provider == "fastembed"
