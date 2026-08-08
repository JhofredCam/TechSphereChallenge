"""FastAPI application for the local post-operative voice agent."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .database import Database, init_database
from .schemas import DocumentStatus
from .services.agent import AgentService
from .services.calls import CallService
from .services.documents import DocumentService
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
    text: str = Field(min_length=1, max_length=5000)


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


def _document_payload(record: Any) -> dict[str, Any]:
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
    }
    return _json_safe(payload)


def _fts5_available(database: Database) -> bool:
    try:
        database.execute("SELECT 1 FROM chunks_fts LIMIT 1").fetchone()
    except Exception:
        return False
    return True


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
    calls = CallService(effective_database, agent=agent, metrics=metrics)
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
        return page("call.html")

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
        }

    @application.get("/api/admin/documents")
    def list_documents() -> dict[str, Any]:
        records = [_document_payload(record) for record in documents.list()]
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
            record = documents.upload(
                content,
                filename,
                mime_type=file.content_type,
                process=True,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _document_payload(record)

    @application.delete("/api/admin/documents/{document_id}")
    def delete_document(document_id: str) -> dict[str, Any]:
        if not documents.delete(document_id):
            raise HTTPException(status_code=404, detail=f"documento no encontrado: {document_id}")
        return {
            "deleted": True,
            "document_id": document_id,
            "status": "deleted",
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
            response = calls.handle_turn(call_id, text)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"no se pudo procesar el turno: {exc}",
            ) from exc
        return _json_safe(response)

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
    async def add_audio(call_id: str, audio: UploadFile = File(...)) -> dict[str, Any]:
        require_call(call_id)
        content = await audio.read(effective_settings.max_upload_bytes + 1)
        try:
            transcript = voice.transcribe(
                content,
                filename=audio.filename or "audio.webm",
                content_type=audio.content_type,
            )
        except VoiceUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            response = calls.handle_turn(call_id, transcript)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
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
