"""FastAPI application for the local post-operative voice agent."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Mapping
from urllib.parse import quote

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, model_validator
from starlette.concurrency import run_in_threadpool

from .config import Settings
from .database import Database, init_database
from .schemas import DocumentStatus
from .services.agent import AgentService
from .services.calls import CallService, LateTranscriptError, ListenEventError
from .services.documents import (
    DocumentNotSearchableError,
    DocumentProcessingError,
    DocumentService,
    SourceFormatNotSupportedError,
    SourceReadError,
    SourceUnavailableError,
)
from .services.ingestion import SUPPORTED_SUFFIXES
from .services.metrics import DEFAULT_MODEL_VERSION, MetricsService
from .services.rag import RagService
from .services.voice import VoiceService, VoiceUnavailable

WEB_DIR = Path(__file__).resolve().parent / "web"


class StartCallRequest(BaseModel):
    """Input accepted by the browser call form."""

    patient_id: str | None = Field(default=None, max_length=200)
    name: str | None = Field(default=None, max_length=200)
    procedure: str = Field(default="seguimiento postoperatorio", max_length=200)
    day_postop: int | None = Field(default=None, ge=0, le=3650)


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=5000)
    client_turn_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
    )
    listen_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
    )
    elapsed_ms: StrictInt | StrictFloat | None = Field(default=None, ge=0, le=300000)

    @model_validator(mode="after")
    def validate_turn_identifiers(self) -> "TurnRequest":
        if (self.client_turn_id is None) != (self.listen_id is None):
            raise ValueError("client_turn_id y listen_id deben enviarse juntos")
        return self


VOICE_EVENT_TYPES = Literal[
    "patient_listen_started",
    "vad_speech_started",
    "vad_silence_started",
    "vad_segment_finalized",
    "partial",
    "final",
    "ended",
    "no_response",
    "timeout",
    "error",
    "retry",
]


class VoiceEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: VOICE_EVENT_TYPES
    listen_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
    )
    client_turn_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
    )
    elapsed_ms: StrictInt | StrictFloat | None = Field(default=None, ge=0, le=300000)
    locale: Literal["es-CO"] = "es-CO"
    implementation: Literal["SpeechRecognition", "webkitSpeechRecognition"] = (
        "SpeechRecognition"
    )
    configured_timeout_ms: StrictInt | None = Field(default=None, ge=1000, le=300000)
    silence_timeout_ms: StrictInt | None = Field(default=None, ge=500, le=10000)
    sequence: StrictInt | None = Field(default=None, ge=0, le=1000000)
    error_code: str | None = Field(
        default=None,
        max_length=64,
        pattern=r"[A-Za-z0-9_.-]{1,64}",
    )

    @model_validator(mode="after")
    def require_client_id_for_final(self) -> "VoiceEventRequest":
        if self.event_type == "final" and self.client_turn_id is None:
            raise ValueError("final requiere client_turn_id")
        return self


class VoiceTimingRequest(BaseModel):
    """Browser timestamps for the start of an agent's spoken response."""

    speech_ended_at: str | int | float
    audio_started_at: str | int | float


class FinishCallRequest(BaseModel):
    symptoms: list[str] | str | None = None
    decision: str | None = Field(default=None, max_length=40)
    alert: bool | None = None
    next_steps: list[str] | None = None
    summary: dict[str, Any] | None = None


def _json_safe(value: Any) -> Any:
    """Convert service records, dataclasses, enums, and nested values to JSON data."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_safe(model_dump())
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_safe(to_dict())
    if hasattr(value, "isoformat") and callable(value.isoformat):
        return value.isoformat()
    return str(value)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _document_payload(record: Any, corpus_revision: int = 0) -> dict[str, Any]:
    status = (
        record.status.value
        if isinstance(record.status, DocumentStatus)
        else str(record.status)
    )
    payload = {
        "id": record.id,
        "document_id": record.id,
        "filename": record.filename,
        "sha256": record.sha256,
        "size_bytes": record.size_bytes,
        "mime_type": record.mime_type,
        "status": status,
        "error": record.error,
        "created_at": record.created_at,
        "processed_at": record.processed_at,
        "available": status == DocumentStatus.AVAILABLE.value,
        "needs_ocr": status == DocumentStatus.NEEDS_OCR.value,
        "enabled": bool(record.enabled),
        "rag_eligible": bool(record.rag_eligible),
        "page_count": int(record.page_count),
        "chunk_count": int(record.chunk_count),
        "preview_available": bool(record.preview_available),
        "source_format": _source_format(record.filename),
        "source_media_type": _source_media_type(record.filename),
        "original_preview_available": status
        not in {DocumentStatus.PROCESSING.value, DocumentStatus.ERROR.value},
        "corpus_revision": corpus_revision,
    }
    return _json_safe(payload)


def _source_format(filename: str | None) -> str | None:
    suffix = Path(str(filename or "")).suffix.casefold()
    return {".pdf": "pdf", ".txt": "txt", ".md": "md"}.get(suffix)


def _source_media_type(filename: str | None) -> str | None:
    suffix = Path(str(filename or "")).suffix.casefold()
    return {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/plain",
    }.get(suffix)


def _source_download_name(filename: str) -> str:
    """Keep Content-Disposition free of path, quote, and control characters."""

    name = Path(str(filename or "document").replace("\\", "/")).name
    name = "".join(
        character for character in name if ord(character) >= 32 and ord(character) != 127
    )
    name = name.replace('"', "'").replace("/", "_").replace("\\", "_").strip(" .")
    return name or "document"


def _fts5_available(database: Database) -> bool:
    try:
        row = database.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("chunks_fts",),
        ).fetchone()
    except Exception:
        return False
    return row is not None


def _admin_error(status_code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": error_code, "message": message},
    )


def _parse_preview_query(value: str, name: str, *, minimum: int) -> int:
    if not isinstance(value, str) or not value or not value.isascii() or not value.isdigit():
        raise _admin_error(422, "invalid_preview_range", f"{name} debe ser un entero valido")
    parsed = int(value)
    if parsed < minimum:
        raise _admin_error(422, "invalid_preview_range", f"{name} esta fuera de rango")
    return parsed


def create_app(
    settings: Settings | None = None,
    *,
    database: Database | None = None,
) -> FastAPI:
    """Create one application and its one local service graph.

    Tests can pass a temporary ``Settings`` and initialized ``Database``.  The
    production module-level instance below uses ``Settings.from_env()``.
    """

    effective_settings = settings or Settings.from_env()
    effective_database = database or init_database(effective_settings)
    metrics = MetricsService(effective_database)
    documents = DocumentService(effective_database, effective_settings)
    rag = RagService(effective_database)
    agent = AgentService(rag)
    calls = CallService(
        effective_database,
        agent=agent,
        metrics=metrics,
        configured_timeout_ms=effective_settings.patient_listen_timeout_ms,
    )
    voice = VoiceService(max_bytes=effective_settings.max_upload_bytes)

    application = FastAPI(
        title="Seguimiento postoperatorio por voz",
        description="Agente local en espanol con conocimiento clinico trazable.",
        version="1.0.0",
    )
    application.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    application.state.settings = effective_settings
    application.state.database = effective_database
    application.state.db = effective_database
    application.state.document_service = documents
    application.state.documents = documents
    application.state.rag_service = rag
    application.state.rag = rag
    application.state.agent_service = agent
    application.state.agent = agent
    application.state.call_service = calls
    application.state.calls = calls
    application.state.metrics_service = metrics
    application.state.metrics = metrics
    application.state.voice_service = voice
    application.state.voice = voice
    application.state.call_contexts: dict[str, dict[str, Any]] = {}

    def page(filename: str) -> FileResponse:
        return FileResponse(WEB_DIR / filename, media_type="text/html")

    def call_context(call_id: str) -> dict[str, Any]:
        return dict(application.state.call_contexts.get(call_id, {}))

    def call_payload(call_id: str) -> dict[str, Any] | None:
        record = calls.get_call(call_id)
        if record is None:
            return None
        payload = dict(_json_safe(record))
        context = call_context(call_id)
        for key, value in context.items():
            if value is not None:
                payload[key] = _json_safe(value)
        payload["turns"] = _json_safe(calls.list_turns(call_id))
        payload["sources"] = _json_safe(calls.get_sources(call_id=call_id))
        return payload

    def require_call(call_id: str) -> dict[str, Any]:
        payload = call_payload(call_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"llamada no encontrada: {call_id}")
        return payload

    @application.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return page("index.html")

    @application.get("/patient", include_in_schema=False)
    def patient_page() -> FileResponse:
        return page("patient-access.html")

    @application.get("/admin/access", include_in_schema=False)
    def admin_access_page() -> FileResponse:
        return page("admin-access.html")

    @application.get("/admin", include_in_schema=False)
    def admin_page() -> FileResponse:
        return page("admin.html")

    @application.get("/call", include_in_schema=False)
    def call_page() -> FileResponse:
        return page("call.html")

    @application.get("/health")
    def health() -> dict[str, Any]:
        document_count = len(documents.list())
        model_id = getattr(agent, "model", DEFAULT_MODEL_VERSION)
        return {
            "status": "ok",
            "model_family": "Meta Llama",
            "model_id": model_id,
            "model": model_id,
            "model_info": {"family": "Meta Llama", "id": model_id},
            "fts5": _fts5_available(effective_database),
            "fts5_available": _fts5_available(effective_database),
            "documents": document_count,
            "docs_count": document_count,
            "corpus_revision": documents.corpus_revision,
            "voice_mode": voice.mode,
            "patient_listen_timeout_ms": effective_settings.patient_listen_timeout_ms,
            "voice_silence_timeout_ms": effective_settings.voice_silence_timeout_ms,
            "voice_vad_rms_threshold": effective_settings.voice_vad_rms_threshold,
            "voice_speech_start_timeout_ms": effective_settings.voice_speech_start_timeout_ms,
        }

    @application.get("/api/admin/documents")
    def list_documents() -> dict[str, Any]:
        records = [
            _document_payload(record, documents.corpus_revision)
            for record in documents.list()
        ]
        return {"documents": records, "count": len(records)}

    @application.post("/api/admin/documents")
    async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
        filename = file.filename or ""
        suffix = Path(filename.replace("\\", "/")).suffix.casefold()
        if suffix not in SUPPORTED_SUFFIXES:
            allowed = ", ".join(sorted(SUPPORTED_SUFFIXES))
            raise HTTPException(
                status_code=415,
                detail=f"extension no soportada; use uno de: {allowed}",
            )
        content = await file.read(effective_settings.max_upload_bytes + 1)
        if len(content) > effective_settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    "el documento supera el limite configurado de "
                    f"{effective_settings.max_upload_bytes} bytes"
                ),
            )
        try:
            record = await run_in_threadpool(
                documents.upload,
                content,
                filename,
                mime_type=file.content_type,
                process=True,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _document_payload(record, documents.corpus_revision)

    @application.get("/api/admin/documents/{document_id}/preview")
    def preview_document(
        document_id: str,
        page: str = "1",
        offset: str = "0",
        limit: str = "8000",
    ) -> dict[str, Any]:
        page_number = _parse_preview_query(page, "page", minimum=1)
        page_offset = _parse_preview_query(offset, "offset", minimum=0)
        page_limit = _parse_preview_query(limit, "limit", minimum=1)
        if page_limit > 8000:
            raise _admin_error(422, "invalid_preview_range", "limit no puede superar 8000")
        try:
            return _json_safe(
                documents.preview(
                    document_id,
                    page=page_number,
                    offset=page_offset,
                    limit=page_limit,
                )
            )
        except KeyError as exc:
            raise _admin_error(404, "document_not_found", str(exc)) from exc
        except LookupError as exc:
            raise _admin_error(404, "page_not_found", str(exc)) from exc
        except DocumentProcessingError as exc:
            raise _admin_error(409, "document_processing", str(exc)) from exc
        except DocumentNotSearchableError as exc:
            raise _admin_error(409, "document_not_searchable", str(exc)) from exc
        except ValueError as exc:
            error_code = str(exc)
            if error_code not in {"invalid_preview_range", "offset_out_of_range"}:
                error_code = "invalid_preview_range"
            raise _admin_error(422, error_code, str(exc)) from exc

    @application.get("/api/admin/documents/{document_id}/source")
    def source_document(document_id: str) -> Response:
        try:
            record, content, source_format, media_type = documents.source(document_id)
        except KeyError as exc:
            raise _admin_error(404, "document_not_found", "No encontramos esta fuente.") from exc
        except DocumentProcessingError as exc:
            raise _admin_error(
                409,
                "document_processing",
                "La fuente aun se esta procesando.",
            ) from exc
        except SourceFormatNotSupportedError as exc:
            raise _admin_error(
                415,
                "source_format_not_supported",
                "Este formato no se puede previsualizar aqui.",
            ) from exc
        except SourceUnavailableError as exc:
            raise _admin_error(
                409,
                "source_unavailable",
                "No pudimos abrir el archivo original.",
            ) from exc
        except SourceReadError as exc:
            raise _admin_error(
                503,
                "source_read_error",
                "No pudimos abrir esta fuente. Intentalo de nuevo.",
            ) from exc

        safe_name = _source_download_name(record.filename)
        ascii_name = safe_name.encode("ascii", "ignore").decode("ascii") or "document"
        headers = {
            "Cache-Control": "no-store",
            "Content-Disposition": (
                f'inline; filename="{ascii_name}"; '
                f"filename*=UTF-8''{quote(safe_name, safe='')}"
            ),
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Source-Format": source_format,
        }
        return Response(content=content, media_type=media_type, headers=headers)

    @application.patch("/api/admin/documents/{document_id}")
    def update_document(document_id: str, payload: Any = Body(default=None)) -> dict[str, Any]:
        if (
            not isinstance(payload, dict)
            or set(payload) != {"enabled"}
            or type(payload.get("enabled")) is not bool
        ):
            raise _admin_error(
                422,
                "invalid_publication_state",
                "el cuerpo debe contener unicamente enabled como booleano",
            )
        try:
            record, changed, revision = documents.set_enabled(
                document_id,
                payload["enabled"],
            )
        except KeyError as exc:
            raise _admin_error(404, "document_not_found", str(exc)) from exc
        except DocumentNotSearchableError as exc:
            raise _admin_error(409, "document_not_searchable", str(exc)) from exc
        except ValueError as exc:
            if str(exc) == "document_not_searchable":
                raise _admin_error(409, "document_not_searchable", str(exc)) from exc
            raise _admin_error(422, "invalid_publication_state", str(exc)) from exc
        response = _document_payload(record, revision)
        response["changed"] = changed
        return response

    @application.delete("/api/admin/documents/{document_id}")
    def delete_document(document_id: str) -> dict[str, Any]:
        if not documents.delete(document_id):
            raise _admin_error(
                404,
                "document_not_found",
                f"documento no encontrado: {document_id}",
            )
        return {
            "deleted": True,
            "document_id": document_id,
            "status": "deleted",
            "corpus_revision": documents.corpus_revision,
        }

    @application.post("/api/calls")
    def start_call(request: StartCallRequest) -> dict[str, Any]:
        patient_id = _clean(request.patient_id)
        name = _clean(request.name)
        if patient_id is None and name is None:
            raise HTTPException(
                status_code=422,
                detail="debe indicar patient_id o name para iniciar la llamada",
            )
        procedure = _clean(request.procedure) or "seguimiento postoperatorio"
        try:
            record = calls.start_call(patient_id=patient_id or name, procedure=procedure)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        call_id = str(record["id"])
        application.state.call_contexts[call_id] = {
            "patient_id": patient_id or name,
            "name": name,
            "procedure": procedure,
            "day_postop": request.day_postop,
        }
        payload = call_payload(call_id)
        assert payload is not None
        return payload

    @application.get("/api/calls/{call_id}")
    def get_call(call_id: str) -> dict[str, Any]:
        return require_call(call_id)

    @application.post("/api/calls/{call_id}/turns")
    def add_turn(call_id: str, request: TurnRequest) -> dict[str, Any]:
        require_call(call_id)
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="text no puede estar vacio")
        try:
            response = calls.handle_turn(
                call_id,
                text,
                client_turn_id=request.client_turn_id,
                listen_id=request.listen_id,
                elapsed_ms=request.elapsed_ms,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except LateTranscriptError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": exc.code,
                    "message": "el transcript llego despues del timeout",
                },
            ) from exc
        except ListenEventError as exc:
            raise HTTPException(
                status_code=409,
                detail={"error_code": exc.code, "message": str(exc)},
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"no se pudo procesar el turno: {exc}",
            ) from exc
        return _json_safe(response)

    @application.post("/api/calls/{call_id}/voice-events")
    def add_voice_event(call_id: str, request: VoiceEventRequest) -> dict[str, Any]:
        """Persist bounded listening telemetry without accepting transcript payloads."""

        require_call(call_id)
        try:
            event = calls.record_voice_event(
                call_id,
                event_type=request.event_type,
                listen_id=request.listen_id,
                client_turn_id=request.client_turn_id,
                elapsed_ms=request.elapsed_ms,
                locale=request.locale,
                implementation=request.implementation,
                error_code=request.error_code,
                configured_timeout_ms=request.configured_timeout_ms,
                silence_timeout_ms=request.silence_timeout_ms,
                sequence=request.sequence,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except LateTranscriptError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": exc.code,
                    "message": "el transcript llego despues del timeout",
                },
            ) from exc
        except ListenEventError as exc:
            raise HTTPException(
                status_code=409,
                detail={"error_code": exc.code, "message": str(exc)},
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _json_safe(event)

    @application.post("/api/calls/{call_id}/turns/{turn_id}/voice-timing")
    def record_voice_timing(
        call_id: str,
        turn_id: str,
        request: VoiceTimingRequest,
    ) -> dict[str, Any]:
        """Record browser voice timing without creating another conversational turn."""

        require_call(call_id)
        try:
            timing = calls.record_voice_timing(
                call_id,
                turn_id,
                speech_ended_at=request.speech_ended_at,
                audio_started_at=request.audio_started_at,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        payload = dict(_json_safe(timing))
        payload["recorded"] = True
        return payload

    @application.post("/api/calls/{call_id}/audio")
    async def add_audio(
        call_id: str,
        audio: UploadFile = File(...),
        client_turn_id: str | None = Query(default=None, min_length=1, max_length=128),
        listen_id: str | None = Query(default=None, min_length=1, max_length=128),
        elapsed_ms: float | None = Query(default=None, ge=0, le=300000),
    ) -> dict[str, Any]:
        require_call(call_id)
        if (client_turn_id is None) != (listen_id is None):
            raise HTTPException(
                status_code=422,
                detail="client_turn_id y listen_id deben enviarse juntos",
            )
        content = await audio.read(effective_settings.max_upload_bytes + 1)
        if len(content) > effective_settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail="el audio supera el limite configurado",
            )
        try:
            transcript = await run_in_threadpool(
                voice.transcribe,
                content,
                filename=audio.filename or "audio.webm",
                content_type=audio.content_type,
            )
        except VoiceUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            response = await run_in_threadpool(
                calls.handle_turn,
                call_id,
                transcript,
                client_turn_id=client_turn_id,
                listen_id=listen_id,
                elapsed_ms=elapsed_ms,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except LateTranscriptError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": exc.code,
                    "message": "el transcript llego despues del timeout",
                },
            ) from exc
        except ListenEventError as exc:
            raise HTTPException(
                status_code=409,
                detail={"error_code": exc.code, "message": str(exc)},
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        response_data = dict(_json_safe(response))
        response_data["transcript"] = transcript
        return response_data

    @application.post("/api/calls/{call_id}/finish")
    def finish_call(
        call_id: str,
        request: FinishCallRequest | None = Body(default=None),
    ) -> dict[str, Any]:
        current = require_call(call_id)
        if current.get("status") != "active":
            raise HTTPException(status_code=409, detail="la llamada ya esta cerrada")
        request = request or FinishCallRequest()
        context = call_context(call_id)
        summary = dict(request.summary or {})
        if context.get("name") is not None:
            summary.setdefault("name", context["name"])
        if context.get("day_postop") is not None:
            summary.setdefault("day_postop", context["day_postop"])
        try:
            calls.close_call(
                call_id,
                patient_id=context.get("patient_id"),
                procedure=context.get("procedure"),
                symptoms=request.symptoms,
                decision=request.decision,
                alert=request.alert,
                next_steps=request.next_steps,
                summary=summary,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        payload = call_payload(call_id)
        assert payload is not None
        return payload

    @application.get("/api/metrics")
    def get_metrics() -> dict[str, Any]:
        return _json_safe(metrics.aggregate())

    return application


app = create_app()


__all__ = ["app", "create_app"]
