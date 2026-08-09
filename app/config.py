"""Path-based application settings.

The foundation deliberately keeps configuration small and local.  Environment variables
are supported for the eventual web application, but no provider credentials or network
clients are created here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
DEFAULT_PATIENT_LISTEN_TIMEOUT_MS = 30_000
MIN_PATIENT_LISTEN_TIMEOUT_MS = 1_000
MAX_PATIENT_LISTEN_TIMEOUT_MS = 300_000
DEFAULT_VOICE_SILENCE_TIMEOUT_MS = 2_000
MIN_VOICE_SILENCE_TIMEOUT_MS = 500
MAX_VOICE_SILENCE_TIMEOUT_MS = 10_000
DEFAULT_VOICE_VAD_RMS_THRESHOLD = 0.025
MIN_VOICE_VAD_RMS_THRESHOLD = 0.001
MAX_VOICE_VAD_RMS_THRESHOLD = 0.2
DEFAULT_VOICE_SPEECH_START_TIMEOUT_MS = 10_000
MIN_VOICE_SPEECH_START_TIMEOUT_MS = 1_000
MAX_VOICE_SPEECH_START_TIMEOUT_MS = 30_000

RAG_PROFILES = frozenset({"challenge-local", "staging", "production"})
RAG_BACKENDS = frozenset({"fts5", "chroma", "hybrid"})
EMBEDDING_PROVIDERS = frozenset({"none", "sentence_transformers", "fastembed", "http"})
VECTOR_STORE_TYPES = frozenset({"fts5", "chroma"})
VECTOR_STORE_MODES = frozenset({"embedded", "server"})
DISTANCE_METRICS = frozenset({"cosine", "l2", "ip"})


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


def _env_text(environ: Mapping[str, str], name: str, default: str) -> str:
    value = environ.get(name, default)
    return str(value).strip() if value is not None else default


def _env_choice(
    environ: Mapping[str, str], name: str, default: str, choices: set[str] | frozenset[str]
) -> str:
    value = _env_text(environ, name, default)
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise ValueError(f"{name} must be one of: {allowed}")
    return value


def _env_bool(environ: Mapping[str, str], name: str, default: bool) -> bool:
    value = _env_text(environ, name, "true" if default else "false").casefold()
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be a boolean")
    return value in {"true", "1", "yes"}


def _env_float(environ: Mapping[str, str], name: str, default: float) -> float:
    value = _env_text(environ, name, str(default))
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def _bounded_int(
    environ: Mapping[str, str], name: str, default: int, minimum: int, maximum: int
) -> int:
    value = _configured_int(environ, name, default)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class RagSettings:
    """Validated external configuration for the RAG migration.

    The object contains configuration only. It never creates directories, loads an
    embedding model, contacts a provider, or opens Chroma during parsing.
    """

    profile: str = "challenge-local"
    backend: str = "fts5"
    shadow_backend: str = "none"
    fallback_to_fts5: bool = True
    index_version: str = "baseline-fts5-v1"
    config_version: int = 1
    splitter_type: str = "recursive_es_v2"
    chunk_size: int = 1200
    chunk_overlap: int = 200
    chunk_unit: str = "characters"
    chunk_min_size: int = 80
    chunk_max_size: int = 1600
    chunking_version: str = "recursive_es_v2"
    embedding_provider: str = "none"
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_model_revision: str = "unset"
    embedding_dimension: int = 1024
    embedding_device: str = "cpu"
    embedding_batch_size: int = 16
    embedding_max_length: int = 512
    embedding_normalize: bool = True
    embedding_query_prefix: str = ""
    embedding_document_prefix: str = ""
    embedding_allow_download: bool = False
    embedding_cache_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR / "models")
    embedding_timeout_ms: int = 350
    embedding_endpoint: str = ""
    vector_store_type: str = "fts5"
    vector_store_mode: str = "embedded"
    vector_store_path: Path = field(default_factory=lambda: DEFAULT_DATA_DIR / "chroma")
    vector_store_host: str = "127.0.0.1"
    vector_store_port: int = 8001
    collection_name: str = "techsphere_rag"
    collection_prefix: str = "clinical_es"
    distance_metric: str = "cosine"
    vector_space_version: str = "cosine-v1"
    vector_upsert_batch_size: int = 64
    vector_query_timeout_ms: int = 100
    vector_delete_timeout_ms: int = 1000
    vector_store_tls: bool = False
    vector_store_auth_token: str = ""
    top_k: int = 5
    vector_top_k: int = 8
    vector_fetch_k: int = 32
    lexical_top_k: int = 8
    similarity_threshold: float = 0.35
    rrf_k: int = 60
    context_max_tokens: int = 1800
    max_chunks_to_prompt: int = 4
    query_timeout_ms: int = 500
    retry_count: int = 0
    cache_query_ttl_seconds: int = 600
    cache_query_max_entries: int = 1024
    groq_chat_timeout_ms: int = 12_000
    groq_whisper_timeout_ms: int = 30_000
    sqlite_busy_timeout_ms: int = 5_000
    langchain_tracing: bool = False
    langchain_project: str = "techsphere-rag"
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langsmith_sample_rate: float = 0.10
    langsmith_capture_content: bool = False
    langsmith_redact_pii: bool = True
    langsmith_trace_retention_days: int = 7
    observability_env: str = "local"
    trace_latency_budget_ms: int = 20

    def __post_init__(self) -> None:
        if self.profile not in RAG_PROFILES:
            raise ValueError(f"invalid RAG profile: {self.profile}")
        if self.backend not in RAG_BACKENDS:
            raise ValueError(f"invalid RAG backend: {self.backend}")
        if self.vector_store_type not in VECTOR_STORE_TYPES:
            raise ValueError(f"invalid vector store type: {self.vector_store_type}")
        if self.vector_store_mode not in VECTOR_STORE_MODES:
            raise ValueError(f"invalid vector store mode: {self.vector_store_mode}")
        if self.embedding_provider not in EMBEDDING_PROVIDERS:
            raise ValueError(f"invalid embedding provider: {self.embedding_provider}")
        if self.distance_metric not in DISTANCE_METRICS:
            raise ValueError(f"invalid distance metric: {self.distance_metric}")
        if self.chunk_overlap >= self.chunk_size or self.chunk_size <= 0:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.chunk_min_size <= 0 or self.chunk_max_size < self.chunk_size:
            raise ValueError("chunk size bounds are inconsistent")
        if self.embedding_dimension <= 0 or self.embedding_batch_size <= 0:
            raise ValueError("embedding dimension and batch size must be positive")
        if self.top_k <= 0 or self.vector_fetch_k < self.vector_top_k:
            raise ValueError("retrieval limits are inconsistent")
        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("SIMILARITY_THRESHOLD must be between 0 and 1")
        if not 0 <= self.langsmith_sample_rate <= 1:
            raise ValueError("LANGSMITH_SAMPLE_RATE must be between 0 and 1")
        if (
            self.profile == "production"
            and self.langsmith_capture_content
            and not self.langsmith_redact_pii
        ):
            raise ValueError(
                "production tracing requires redaction when content capture is enabled"
            )
        if self.profile in {"staging", "production"} and self.embedding_provider == "none":
            raise ValueError("staging and production require an embedding provider")
        if self.profile == "production" and not self.fallback_to_fts5:
            raise ValueError("production requires RAG_FALLBACK_TO_FTS5=true")
        if self.vector_store_mode == "server" and not self.vector_store_host:
            raise ValueError("VECTOR_STORE_HOST is required in server mode")

    @property
    def rag_index_name(self) -> str:
        return f"{self.collection_prefix}_{self.chunking_version}_{self.index_version}"

    def effective_dict(self, *, redact_secrets: bool = True) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, Path):
                value = str(value)
            if redact_secrets and name in {"vector_store_auth_token", "embedding_endpoint"}:
                value = "[redacted]" if value else ""
            values[name] = value
        return values


def build_rag_settings(
    environ: Mapping[str, str] | None = None,
    *,
    project_root: Path | None = None,
    data_dir: Path | None = None,
) -> RagSettings:
    """Parse and validate RAG variables without touching disk."""

    values = os.environ if environ is None else environ
    root = (project_root or PROJECT_ROOT).expanduser().resolve()
    configured_data_dir = data_dir or _configured_path(
        values.get("APP_DATA_DIR", values.get("DATA_DIR")), root / "data", root
    )
    profile = _env_choice(values, "RAG_PROFILE", "challenge-local", RAG_PROFILES)
    canonical_chunk_size = _configured_int(values, "CHUNK_SIZE", 1200)
    canonical_chunk_overlap = _configured_int(values, "CHUNK_OVERLAP", 200)
    legacy_size = values.get("APP_CHUNK_SIZE")
    legacy_overlap = values.get("APP_CHUNK_OVERLAP")
    if legacy_size is not None and "CHUNK_SIZE" not in values:
        canonical_chunk_size = _configured_int(values, "APP_CHUNK_SIZE", canonical_chunk_size)
    if legacy_overlap is not None and "CHUNK_OVERLAP" not in values:
            canonical_chunk_overlap = _configured_int(
                values, "APP_CHUNK_OVERLAP", canonical_chunk_overlap
            )
    vector_store_type = _env_text(
        values, "VECTOR_STORE_TYPE", "fts5" if profile == "challenge-local" else "chroma"
    )
    settings = RagSettings(
        profile=profile,
        backend=_env_choice(values, "RAG_BACKEND", "fts5", RAG_BACKENDS),
        shadow_backend=_env_text(values, "RAG_SHADOW_BACKEND", "none"),
        fallback_to_fts5=_env_bool(values, "RAG_FALLBACK_TO_FTS5", True),
        index_version=_env_text(values, "RAG_INDEX_VERSION", "baseline-fts5-v1"),
        config_version=_bounded_int(values, "RAG_CONFIG_VERSION", 1, 1, 100),
        splitter_type=_env_text(values, "SPLITTER_TYPE", "recursive_es_v2"),
        chunk_size=canonical_chunk_size,
        chunk_overlap=canonical_chunk_overlap,
        chunk_unit=_env_choice(values, "CHUNK_UNIT", "characters", {"characters", "tokens"}),
        chunk_min_size=_bounded_int(values, "CHUNK_MIN_SIZE", 80, 1, 100_000),
        chunk_max_size=_bounded_int(values, "CHUNK_MAX_SIZE", 1600, 1, 100_000),
        chunking_version=_env_text(values, "CHUNKING_VERSION", "recursive_es_v2"),
        embedding_provider=_env_choice(values, "EMBEDDING_PROVIDER", "none", EMBEDDING_PROVIDERS),
        embedding_model_name=_env_text(values, "EMBEDDING_MODEL_NAME", "BAAI/bge-m3"),
        embedding_model_revision=_env_text(values, "EMBEDDING_MODEL_REVISION", "unset"),
        embedding_dimension=_bounded_int(values, "EMBEDDING_DIMENSION", 1024, 1, 16_384),
        embedding_device=_env_text(values, "EMBEDDING_DEVICE", "cpu"),
        embedding_batch_size=_bounded_int(values, "EMBEDDING_BATCH_SIZE", 16, 1, 4096),
        embedding_max_length=_bounded_int(values, "EMBEDDING_MAX_LENGTH", 512, 1, 32_768),
        embedding_normalize=_env_bool(values, "EMBEDDING_NORMALIZE", True),
        embedding_query_prefix=_env_text(values, "EMBEDDING_QUERY_PREFIX", ""),
        embedding_document_prefix=_env_text(values, "EMBEDDING_DOCUMENT_PREFIX", ""),
        embedding_allow_download=_env_bool(values, "EMBEDDING_ALLOW_DOWNLOAD", False),
        embedding_cache_dir=_configured_path(
            values.get("EMBEDDING_CACHE_DIR"), configured_data_dir / "models", root
        ),
        embedding_timeout_ms=_bounded_int(values, "EMBEDDING_TIMEOUT_MS", 350, 1, 120_000),
        embedding_endpoint=_env_text(values, "EMBEDDING_ENDPOINT", ""),
        vector_store_type=vector_store_type,
        vector_store_mode=_env_choice(
            values, "VECTOR_STORE_MODE", "embedded", VECTOR_STORE_MODES
        ),
        vector_store_path=_configured_path(
            values.get("VECTOR_STORE_PATH"), configured_data_dir / "chroma", root
        ),
        vector_store_host=_env_text(values, "VECTOR_STORE_HOST", "127.0.0.1"),
        vector_store_port=_bounded_int(values, "VECTOR_STORE_PORT", 8001, 1, 65_535),
        collection_name=_env_text(values, "COLLECTION_NAME", "techsphere_rag"),
        collection_prefix=_env_text(values, "COLLECTION_PREFIX", "clinical_es"),
        distance_metric=_env_choice(values, "DISTANCE_METRIC", "cosine", DISTANCE_METRICS),
        vector_space_version=_env_text(values, "VECTOR_SPACE_VERSION", "cosine-v1"),
        vector_upsert_batch_size=_bounded_int(values, "VECTOR_UPSERT_BATCH_SIZE", 64, 1, 4096),
        vector_query_timeout_ms=_bounded_int(values, "VECTOR_QUERY_TIMEOUT_MS", 100, 1, 120_000),
        vector_delete_timeout_ms=_bounded_int(values, "VECTOR_DELETE_TIMEOUT_MS", 1000, 1, 120_000),
        vector_store_tls=_env_bool(values, "VECTOR_STORE_TLS", False),
        vector_store_auth_token=_env_text(values, "VECTOR_STORE_AUTH_TOKEN", ""),
        top_k=_bounded_int(values, "TOP_K", 5, 1, 100),
        vector_top_k=_bounded_int(values, "VECTOR_TOP_K", 8, 1, 100),
        vector_fetch_k=_bounded_int(values, "VECTOR_FETCH_K", 32, 1, 500),
        lexical_top_k=_bounded_int(values, "LEXICAL_TOP_K", 8, 1, 100),
        similarity_threshold=_env_float(values, "SIMILARITY_THRESHOLD", 0.35),
        rrf_k=_bounded_int(values, "RAG_RRF_K", 60, 1, 10_000),
        context_max_tokens=_bounded_int(values, "RAG_CONTEXT_MAX_TOKENS", 1800, 1, 32_000),
        max_chunks_to_prompt=_bounded_int(values, "RAG_MAX_CHUNKS_TO_PROMPT", 4, 1, 100),
        query_timeout_ms=_bounded_int(values, "RAG_QUERY_TIMEOUT_MS", 500, 1, 120_000),
        retry_count=_bounded_int(values, "RAG_RETRY_COUNT", 0, 0, 10),
        cache_query_ttl_seconds=_bounded_int(values, "RAG_CACHE_QUERY_TTL_SECONDS", 600, 0, 86_400),
        cache_query_max_entries=_bounded_int(
            values, "RAG_CACHE_QUERY_MAX_ENTRIES", 1024, 0, 100_000
        ),
        groq_chat_timeout_ms=_bounded_int(values, "GROQ_CHAT_TIMEOUT_MS", 12_000, 1, 120_000),
        groq_whisper_timeout_ms=_bounded_int(values, "GROQ_WHISPER_TIMEOUT_MS", 30_000, 1, 120_000),
        sqlite_busy_timeout_ms=_bounded_int(values, "SQLITE_BUSY_TIMEOUT_MS", 5_000, 1, 120_000),
        langchain_tracing=_env_bool(values, "LANGCHAIN_TRACING_V2", False),
        langchain_project=_env_text(values, "LANGCHAIN_PROJECT", "techsphere-rag"),
        langchain_endpoint=_env_text(values, "LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
        langsmith_sample_rate=_env_float(values, "LANGSMITH_SAMPLE_RATE", 0.10),
        langsmith_capture_content=_env_bool(values, "LANGSMITH_CAPTURE_CONTENT", False),
        langsmith_redact_pii=_env_bool(values, "LANGSMITH_REDACT_PII", True),
        langsmith_trace_retention_days=_bounded_int(
            values, "LANGSMITH_TRACE_RETENTION_DAYS", 7, 1, 3650
        ),
        observability_env=_env_choice(
            values, "OBSERVABILITY_ENV", "local", {"local", "staging", "production"}
        ),
        trace_latency_budget_ms=_bounded_int(values, "TRACE_LATENCY_BUDGET_MS", 20, 1, 10_000),
    )
    return settings


def validate_patient_listen_timeout_ms(value: int) -> int:
    """Validate the total browser listening duration in milliseconds."""

    if type(value) is not int:
        raise ValueError("patient_listen_timeout_ms must be an integer")
    if not MIN_PATIENT_LISTEN_TIMEOUT_MS <= value <= MAX_PATIENT_LISTEN_TIMEOUT_MS:
        raise ValueError(
            "patient_listen_timeout_ms must be between "
            f"{MIN_PATIENT_LISTEN_TIMEOUT_MS} and {MAX_PATIENT_LISTEN_TIMEOUT_MS}"
        )
    return value


def _configured_patient_listen_timeout(environ: Mapping[str, str]) -> int:
    """Parse the optional environment override without accepting an empty value."""

    if "PATIENT_LISTEN_TIMEOUT_MS" not in environ:
        return DEFAULT_PATIENT_LISTEN_TIMEOUT_MS
    raw_value = environ.get("PATIENT_LISTEN_TIMEOUT_MS")
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError("PATIENT_LISTEN_TIMEOUT_MS must not be empty")
    try:
        value = int(raw_value.strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("PATIENT_LISTEN_TIMEOUT_MS must be an integer") from exc
    try:
        return validate_patient_listen_timeout_ms(value)
    except ValueError as exc:
        raise ValueError(f"PATIENT_LISTEN_TIMEOUT_MS: {exc}") from exc


def validate_voice_silence_timeout_ms(value: int) -> int:
    valid = (
        type(value) is int
        and MIN_VOICE_SILENCE_TIMEOUT_MS <= value <= MAX_VOICE_SILENCE_TIMEOUT_MS
    )
    if not valid:
        raise ValueError(
            "voice_silence_timeout_ms must be between "
            f"{MIN_VOICE_SILENCE_TIMEOUT_MS} and {MAX_VOICE_SILENCE_TIMEOUT_MS}"
        )
    return value


def validate_voice_vad_rms_threshold(value: float) -> float:
    valid = (
        not isinstance(value, bool)
        and MIN_VOICE_VAD_RMS_THRESHOLD <= float(value) <= MAX_VOICE_VAD_RMS_THRESHOLD
    )
    if not valid:
        raise ValueError(
            "voice_vad_rms_threshold must be between "
            f"{MIN_VOICE_VAD_RMS_THRESHOLD} and {MAX_VOICE_VAD_RMS_THRESHOLD}"
        )
    return float(value)


def validate_voice_speech_start_timeout_ms(value: int) -> int:
    valid = (
        type(value) is int
        and MIN_VOICE_SPEECH_START_TIMEOUT_MS <= value <= MAX_VOICE_SPEECH_START_TIMEOUT_MS
    )
    if not valid:
        raise ValueError(
            "voice_speech_start_timeout_ms must be between "
            f"{MIN_VOICE_SPEECH_START_TIMEOUT_MS} and {MAX_VOICE_SPEECH_START_TIMEOUT_MS}"
        )
    return value


def _configured_vad_int(environ: Mapping[str, str], name: str, default: int, validator: Any) -> int:
    raw = environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    try:
        return validator(value)
    except ValueError as exc:
        raise ValueError(f"{name}: {exc}") from exc


def _configured_vad_float(environ: Mapping[str, str], name: str, default: float) -> float:
    raw = environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        value = float(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    try:
        return validate_voice_vad_rms_threshold(value)
    except ValueError as exc:
        raise ValueError(f"{name}: {exc}") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Filesystem and ingestion settings for one local application instance."""

    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)
    database_path: Path | None = None
    uploads_dir: Path | None = None
    chunk_size: int = 1200
    chunk_overlap: int = 200
    max_upload_bytes: int = MAX_UPLOAD_BYTES
    patient_listen_timeout_ms: int = DEFAULT_PATIENT_LISTEN_TIMEOUT_MS
    voice_silence_timeout_ms: int = DEFAULT_VOICE_SILENCE_TIMEOUT_MS
    voice_vad_rms_threshold: float = DEFAULT_VOICE_VAD_RMS_THRESHOLD
    voice_speech_start_timeout_ms: int = DEFAULT_VOICE_SPEECH_START_TIMEOUT_MS
    rag: RagSettings = field(default_factory=RagSettings)

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
        if self.max_upload_bytes <= 0 or self.max_upload_bytes > MAX_UPLOAD_BYTES:
            raise ValueError(f"max_upload_bytes must be between 1 and {MAX_UPLOAD_BYTES}")
        validate_patient_listen_timeout_ms(self.patient_listen_timeout_ms)
        validate_voice_silence_timeout_ms(self.voice_silence_timeout_ms)
        validate_voice_vad_rms_threshold(self.voice_vad_rms_threshold)
        validate_voice_speech_start_timeout_ms(self.voice_speech_start_timeout_ms)

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
                MAX_UPLOAD_BYTES,
            ),
            patient_listen_timeout_ms=_configured_patient_listen_timeout(values),
            voice_silence_timeout_ms=_configured_vad_int(
                values,
                "VOICE_SILENCE_TIMEOUT_MS",
                DEFAULT_VOICE_SILENCE_TIMEOUT_MS,
                validate_voice_silence_timeout_ms,
            ),
            voice_vad_rms_threshold=_configured_vad_float(
                values,
                "VOICE_VAD_RMS_THRESHOLD",
                DEFAULT_VOICE_VAD_RMS_THRESHOLD,
            ),
            voice_speech_start_timeout_ms=_configured_vad_int(
                values,
                "VOICE_SPEECH_START_TIMEOUT_MS",
                DEFAULT_VOICE_SPEECH_START_TIMEOUT_MS,
                validate_voice_speech_start_timeout_ms,
            ),
            rag=build_rag_settings(values, project_root=root, data_dir=data_dir),
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
    "DEFAULT_PATIENT_LISTEN_TIMEOUT_MS",
    "DEFAULT_VOICE_SILENCE_TIMEOUT_MS",
    "DEFAULT_VOICE_SPEECH_START_TIMEOUT_MS",
    "DEFAULT_VOICE_VAD_RMS_THRESHOLD",
    "MAX_PATIENT_LISTEN_TIMEOUT_MS",
    "MAX_VOICE_SILENCE_TIMEOUT_MS",
    "MAX_VOICE_SPEECH_START_TIMEOUT_MS",
    "MAX_VOICE_VAD_RMS_THRESHOLD",
    "MAX_UPLOAD_BYTES",
    "MIN_PATIENT_LISTEN_TIMEOUT_MS",
    "MIN_VOICE_SILENCE_TIMEOUT_MS",
    "MIN_VOICE_SPEECH_START_TIMEOUT_MS",
    "MIN_VOICE_VAD_RMS_THRESHOLD",
    "PROJECT_ROOT",
    "RAG_PROFILES",
    "RAG_BACKENDS",
    "EMBEDDING_PROVIDERS",
    "VECTOR_STORE_TYPES",
    "VECTOR_STORE_MODES",
    "DISTANCE_METRICS",
    "RagSettings",
    "Settings",
    "build_rag_settings",
    "get_settings",
    "validate_patient_listen_timeout_ms",
    "validate_voice_silence_timeout_ms",
    "validate_voice_speech_start_timeout_ms",
    "validate_voice_vad_rms_threshold",
]
