"""Path-based application settings.

The foundation deliberately keeps configuration small and local.  Environment variables
are supported for the eventual web application, but no provider credentials or network
clients are created here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


def _configured_path(value: str | Path | None, default: Path, base_dir: Path) -> Path:
    path = Path(value) if value is not None else default
    if not path.is_absolute():
        path = base_dir / path
    return path.expanduser().resolve()


def _configured_int(environ: Mapping[str, str], name: str, default: int) -> int:
    value = environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Filesystem and ingestion settings for one local application instance."""

    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)
    database_path: Path | None = None
    uploads_dir: Path | None = None
    chunk_size: int = 1200
    chunk_overlap: int = 200
    max_upload_bytes: int = 25 * 1024 * 1024

    def __post_init__(self) -> None:
        data_dir = Path(self.data_dir).expanduser().resolve()
        database_path = data_dir / "app.sqlite3" if self.database_path is None else Path(
            self.database_path
        ).expanduser()
        uploads_dir = data_dir / "uploads" if self.uploads_dir is None else Path(
            self.uploads_dir
        ).expanduser()
        if not database_path.is_absolute():
            database_path = data_dir / database_path
        if not uploads_dir.is_absolute():
            uploads_dir = data_dir / uploads_dir
        database_path = database_path.resolve()
        uploads_dir = uploads_dir.resolve()

        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be between zero and chunk_size - 1")
        if self.max_upload_bytes <= 0:
            raise ValueError("max_upload_bytes must be greater than zero")

        object.__setattr__(self, "data_dir", data_dir)
        object.__setattr__(self, "database_path", database_path)
        object.__setattr__(self, "uploads_dir", uploads_dir)

    @property
    def db_path(self) -> Path:
        """Short alias used by database bootstrap code."""

        assert self.database_path is not None
        return self.database_path

    @property
    def documents_dir(self) -> Path:
        """Alias for the directory that stores uploaded source files."""

        assert self.uploads_dir is not None
        return self.uploads_dir

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        project_root: Path | None = None,
    ) -> "Settings":
        """Build settings from environment variables without touching the filesystem."""

        values = os.environ if environ is None else environ
        root = (project_root or PROJECT_ROOT).expanduser().resolve()
        data_dir = _configured_path(
            values.get("APP_DATA_DIR", values.get("DATA_DIR")),
            root / "data",
            root,
        )
        database_value = values.get("APP_DATABASE_PATH", values.get("DATABASE_PATH"))
        uploads_value = values.get("APP_UPLOADS_DIR", values.get("UPLOADS_DIR"))
        return cls(
            data_dir=data_dir,
            database_path=(
                None
                if database_value is None
                else _configured_path(database_value, data_dir / "app.sqlite3", root)
            ),
            uploads_dir=(
                None
                if uploads_value is None
                else _configured_path(uploads_value, data_dir / "uploads", root)
            ),
            chunk_size=_configured_int(values, "APP_CHUNK_SIZE", 1200),
            chunk_overlap=_configured_int(values, "APP_CHUNK_OVERLAP", 200),
            max_upload_bytes=_configured_int(
                values,
                "APP_MAX_UPLOAD_BYTES",
                25 * 1024 * 1024,
            ),
        )

    def ensure_directories(self) -> None:
        """Create only the local directories needed by the application."""

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)


def get_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Return settings for the current process."""

    return Settings.from_env(environ)


__all__ = [
    "DEFAULT_DATA_DIR",
    "PROJECT_ROOT",
    "Settings",
    "get_settings",
]
