"""Call, turn, source, and structured closing-summary persistence."""

from __future__ import annotations

import json
import math
import re
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ..config import DEFAULT_PATIENT_LISTEN_TIMEOUT_MS, validate_patient_listen_timeout_ms
from ..database import Database, utc_now
from .messages import display_message, voice_message
from .metrics import VOICE_EVENT_TYPES, MetricsService
from .triage import TriageResult, highest_level, normalize_level


class SerializableRecord(dict[str, Any]):
    """A JSON mapping with convenient attribute access for service callers."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def model_dump(self) -> dict[str, Any]:
        return dict(self)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


_PUBLIC_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_VOICE_IMPLEMENTATIONS = frozenset({"SpeechRecognition", "webkitSpeechRecognition"})
_VOICE_LOCALE = "es-CO"
_ACTIVE_LISTEN_STATUSES = frozenset({"LISTENING", "PARTIAL", "FINAL_RECEIVED"})
_PRE_FINAL_LISTEN_STATUSES = frozenset({"LISTENING", "PARTIAL"})
_TERMINAL_LISTEN_STATUSES = frozenset(
    {
        "NO_RESPONSE",
        "LISTEN_TIMEOUT",
        "RECOGNITION_ERROR",
        "RETRY_REQUIRED",
        "COMPLETED",
    }
)


class ListenEventError(ValueError):
    """A safe, stable conflict raised by the listening-attempt contract."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class LateTranscriptError(ListenEventError):
    """Raised when a transcript arrives after a timeout won the race."""

    def __init__(self) -> None:
        super().__init__("late_transcript")


class CorpusRevisionChangedError(RuntimeError):
    """Raised when retrieved evidence changes before its citation is persisted."""


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (str, bytes)):
        return {"citation": value.decode() if isinstance(value, bytes) else value}
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        return dict(result) if isinstance(result, Mapping) else {}
    result: dict[str, Any] = {}
    for name in (
        "id",
        "source_id",
        "document_id",
        "filename",
        "page_number",
        "chunk_id",
        "chunk_index",
        "document_filename_snapshot",
        "document_sha256_snapshot",
        "sha256",
        "score",
        "citation",
        "corpus_revision",
        "text",
    ):
        if hasattr(value, name):
            result[name] = getattr(value, name)
    return result


def _json_loads(value: Any) -> Any:
    if not value:
        return None
    try:
        return json.loads(str(value))
    except (TypeError, ValueError):
        return None


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class CallService:
    """Persist a browser/API call using the existing SQLite tables."""

    def __init__(
        self,
        database: Database,
        agent: Any | None = None,
        metrics: MetricsService | str | Path | None = None,
        *,
        configured_timeout_ms: int = DEFAULT_PATIENT_LISTEN_TIMEOUT_MS,
    ) -> None:
        self.database = database
        self.agent = agent
        if metrics is None:
            self.metrics = MetricsService(database)
        elif isinstance(metrics, (str, Path)):
            self.metrics = MetricsService(database, metrics)
        else:
            self.metrics = metrics
        self.configured_timeout_ms = validate_patient_listen_timeout_ms(configured_timeout_ms)

    def start_call(
        self,
        patient_id: str | None = None,
        procedure: str | None = None,
        *,
        call_id: str | None = None,
        started_at: str | None = None,
        created_at: str | None = None,
    ) -> SerializableRecord:
        call_id = call_id or _new_id("call")
        timestamp = started_at or utc_now()
        created = created_at or timestamp
        self.database.execute(
            """
            INSERT INTO calls(
                id, patient_id, procedure, status, started_at, ended_at,
                summary_json, triage_level, alert, created_at
            ) VALUES (?, ?, ?, 'active', ?, NULL, NULL, NULL, 0, ?)
            """,
            (call_id, patient_id, procedure, timestamp, created),
        )
        return self.get_call(call_id)  # type: ignore[return-value]

    create_call = start_call
    create = start_call

    def get_call(self, call_id: str) -> SerializableRecord | None:
        row = self.database.execute(
            "SELECT * FROM calls WHERE id = ?",
            (call_id,),
        ).fetchone()
        if row is None:
            return None
        summary = _json_loads(row["summary_json"])
        return SerializableRecord(
            {
                "id": str(row["id"]),
                "call_id": str(row["id"]),
                "patient_id": row["patient_id"],
                "patient": row["patient_id"],
                "procedure": row["procedure"],
                "status": str(row["status"]),
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "summary": summary,
                "summary_json": row["summary_json"],
                "triage_level": row["triage_level"],
                "level": row["triage_level"],
                "alert": bool(row["alert"]),
                "created_at": row["created_at"],
            }
        )

    get = get_call

    def list_calls(self, *, status: str | None = None) -> list[SerializableRecord]:
        if status is None:
            rows = self.database.execute(
                "SELECT id FROM calls ORDER BY created_at DESC, id DESC"
            ).fetchall()
        else:
            rows = self.database.execute(
                "SELECT id FROM calls WHERE status = ? ORDER BY created_at DESC, id DESC",
                (status,),
            ).fetchall()
        records: list[SerializableRecord] = []
        for row in rows:
            record = self.get_call(str(row["id"]))
            if record is not None:
                records.append(record)
        return records

    def _call_row_for_update(self, connection: Any, call_id: str) -> Any:
        row = connection.execute(
            "SELECT id, status, triage_level, alert FROM calls WHERE id = ?",
            (call_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown call: {call_id}")
        if str(row["status"]) != "active":
            raise ValueError(f"call is not active: {call_id}")
        return row

    @staticmethod
    def _source_payload(source: Any, corpus_revision: int) -> dict[str, Any]:
        value = _as_dict(source)
        document_id = value.get("document_id") or None
        chunk_id = value.get("chunk_id") or None
        page_number = value.get("page_number")
        try:
            page_number = int(page_number) if page_number is not None else None
        except (TypeError, ValueError):
            page_number = None
        score = _float_or_none(value.get("score"))
        citation = value.get("citation")
        if not citation:
            filename = value.get("filename") or document_id or "fuente"
            citation = (
                f"{filename} (p. {page_number})" if page_number is not None else str(filename)
            )
        revision = value.get("corpus_revision", corpus_revision)
        try:
            revision = int(revision)
        except (TypeError, ValueError):
            revision = corpus_revision
        chunk_index = value.get("chunk_index")
        try:
            chunk_index = int(chunk_index) if chunk_index is not None else None
        except (TypeError, ValueError):
            chunk_index = None
        return {
            "id": str(value.get("id") or value.get("source_id") or _new_id("source")),
            "document_id": str(document_id) if document_id is not None else None,
            "chunk_id": str(chunk_id) if chunk_id is not None else None,
            "page_number": page_number,
            "score": score,
            "citation": str(citation),
            "corpus_revision": revision,
            "document_filename_snapshot": value.get("document_filename_snapshot")
            or value.get("filename"),
            "document_sha256_snapshot": value.get("document_sha256_snapshot")
            or value.get("sha256"),
            "chunk_index_snapshot": chunk_index,
        }

    @staticmethod
    def _validate_public_id(value: str | None, name: str) -> None:
        if value is None:
            return
        if not isinstance(value, str) or not _PUBLIC_ID_PATTERN.fullmatch(value):
            raise ListenEventError(f"invalid_{name}")

    @staticmethod
    def _validate_elapsed_ms(value: Any | None) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ListenEventError("invalid_elapsed_ms")
        try:
            elapsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ListenEventError("invalid_elapsed_ms") from exc
        if not math.isfinite(elapsed) or elapsed < 0 or elapsed > 300_000:
            raise ListenEventError("invalid_elapsed_ms")
        return elapsed

    @staticmethod
    def _attempt_payload(
        row: Any,
        *,
        event_type: str,
        duplicate: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "call_id": str(row["call_id"]),
            "listen_id": str(row["listen_id"]),
            "event_type": event_type,
            "status": str(row["status"]),
            "duplicate": duplicate,
            "configured_timeout_ms": int(row["configured_timeout_ms"]),
            "elapsed_ms": row["elapsed_ms"],
            "locale": str(row["locale"]),
            "implementation": str(row["implementation"]),
        }
        if row["client_turn_id"] is not None:
            payload["client_turn_id"] = str(row["client_turn_id"])
        if row["error_code"] is not None:
            payload["error_code"] = str(row["error_code"])
        return payload

    @staticmethod
    def _set_attempt(
        connection: Any,
        *,
        listen_id: str,
        status: str,
        client_turn_id: str | None,
        elapsed_ms: float | None,
        locale: str,
        implementation: str,
        error_code: str | None,
        patient_turn_id: str | None = None,
        agent_turn_id: str | None = None,
        response_json: str | None = None,
    ) -> None:
        connection.execute(
            """
            UPDATE listening_attempts
            SET client_turn_id = ?, status = ?, elapsed_ms = ?, locale = ?,
                implementation = ?, error_code = ?, patient_turn_id = ?,
                agent_turn_id = ?, response_json = ?, updated_at = ?
            WHERE listen_id = ?
            """,
            (
                client_turn_id,
                status,
                elapsed_ms,
                locale,
                implementation,
                error_code,
                patient_turn_id,
                agent_turn_id,
                response_json,
                utc_now(),
                listen_id,
            ),
        )

    def _insert_attempt(
        self,
        connection: Any,
        *,
        call_id: str,
        listen_id: str,
        client_turn_id: str | None,
        status: str,
        configured_timeout_ms: int,
        elapsed_ms: float | None,
        locale: str,
        implementation: str,
        error_code: str | None,
    ) -> None:
        timestamp = utc_now()
        connection.execute(
            """
            INSERT INTO listening_attempts(
                listen_id, call_id, client_turn_id, status,
                configured_timeout_ms, elapsed_ms, locale, implementation,
                error_code, patient_turn_id, agent_turn_id, response_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
            """,
            (
                listen_id,
                call_id,
                client_turn_id,
                status,
                configured_timeout_ms,
                elapsed_ms,
                locale,
                implementation,
                error_code,
                timestamp,
                timestamp,
            ),
        )

    def record_voice_event(
        self,
        call_id: str,
        *,
        event_type: str,
        listen_id: str,
        client_turn_id: str | None = None,
        elapsed_ms: Any | None = None,
        locale: str = _VOICE_LOCALE,
        implementation: str = "SpeechRecognition",
        error_code: str | None = None,
        configured_timeout_ms: int | None = None,
        silence_timeout_ms: int | None = None,
        sequence: int | None = None,
    ) -> SerializableRecord:
        """Persist one bounded listening event without creating a clinical turn."""

        if event_type not in VOICE_EVENT_TYPES:
            raise ListenEventError("invalid_voice_event")
        if not isinstance(locale, str) or locale != _VOICE_LOCALE:
            raise ListenEventError("invalid_locale")
        if implementation not in _VOICE_IMPLEMENTATIONS:
            raise ListenEventError("invalid_implementation")
        if error_code is not None:
            if not isinstance(error_code, str) or not re.fullmatch(
                r"[A-Za-z0-9_.-]{1,64}", error_code
            ):
                raise ListenEventError("invalid_error_code")
        self._validate_public_id(listen_id, "listen_id")
        self._validate_public_id(client_turn_id, "client_turn_id")
        elapsed = self._validate_elapsed_ms(elapsed_ms)
        if silence_timeout_ms is not None and not 500 <= int(silence_timeout_ms) <= 10_000:
            raise ListenEventError("invalid_silence_timeout_ms")
        if sequence is not None and (
            isinstance(sequence, bool) or not 0 <= int(sequence) <= 1_000_000
        ):
            raise ListenEventError("invalid_sequence")
        effective_timeout = self.configured_timeout_ms
        if configured_timeout_ms is not None:
            try:
                requested_timeout = validate_patient_listen_timeout_ms(configured_timeout_ms)
            except ValueError as exc:
                raise ListenEventError("invalid_configured_timeout_ms") from exc
            if requested_timeout != effective_timeout:
                raise ListenEventError("timeout_configuration_mismatch")

        should_log = False
        late_error = False
        with self.database.transaction() as connection:
            call_row = connection.execute(
                "SELECT status FROM calls WHERE id = ?",
                (call_id,),
            ).fetchone()
            if call_row is None:
                raise KeyError(f"unknown call: {call_id}")
            if str(call_row["status"]) != "active":
                raise ListenEventError("call_not_active")

            existing_client = None
            if client_turn_id is not None:
                existing_client = connection.execute(
                    "SELECT * FROM listening_attempts WHERE client_turn_id = ?",
                    (client_turn_id,),
                ).fetchone()
                if existing_client is not None and str(existing_client["call_id"]) != str(call_id):
                    raise ListenEventError("client_turn_id_not_for_call")

            row = connection.execute(
                "SELECT * FROM listening_attempts WHERE listen_id = ?",
                (listen_id,),
            ).fetchone()
            if row is not None and str(row["call_id"]) != str(call_id):
                raise ListenEventError("listen_id_not_for_call")
            if row is None and existing_client is not None:
                row = existing_client
                if str(row["listen_id"]) != listen_id:
                    if str(row["status"]) == "LISTEN_TIMEOUT" and event_type == "final":
                        raise LateTranscriptError()
                    return SerializableRecord(
                        self._attempt_payload(row, event_type=event_type, duplicate=True)
                    )

            if row is None:
                initial_status = {
                    "patient_listen_started": "LISTENING",
                    "vad_speech_started": "LISTENING",
                    "vad_silence_started": "LISTENING",
                    "vad_segment_finalized": "PROCESSING",
                    "partial": "PARTIAL",
                    "final": "FINAL_RECEIVED",
                    "ended": "NO_RESPONSE",
                    "no_response": "NO_RESPONSE",
                    "timeout": "LISTEN_TIMEOUT",
                    "error": "RECOGNITION_ERROR",
                    "retry": "RETRY_REQUIRED",
                }[event_type]
                if event_type == "final" and elapsed is not None and elapsed > effective_timeout:
                    initial_status = "LISTEN_TIMEOUT"
                self._insert_attempt(
                    connection,
                    call_id=call_id,
                    listen_id=listen_id,
                    client_turn_id=client_turn_id,
                    status=initial_status,
                    configured_timeout_ms=effective_timeout,
                    elapsed_ms=elapsed,
                    locale=locale,
                    implementation=implementation,
                    error_code=error_code,
                )
                row = connection.execute(
                    "SELECT * FROM listening_attempts WHERE listen_id = ?",
                    (listen_id,),
                ).fetchone()
                should_log = True
                if event_type == "final" and initial_status == "LISTEN_TIMEOUT":
                    late_error = True
            else:
                current_status = str(row["status"])
                stored_client_id = row["client_turn_id"]
                if event_type == "final" and current_status == "LISTEN_TIMEOUT":
                    late_error = True
                elif stored_client_id is not None and client_turn_id != stored_client_id:
                    raise ListenEventError("client_turn_id_mismatch")
                bound_client_id = client_turn_id or stored_client_id
                next_status: str | None = None
                late = late_error
                if event_type == "final":
                    if current_status in _TERMINAL_LISTEN_STATUSES:
                        if current_status != "COMPLETED":
                            late = True
                    elif elapsed is not None and elapsed > int(row["configured_timeout_ms"]):
                        next_status = "LISTEN_TIMEOUT"
                        late = True
                    elif current_status in {"FINAL_RECEIVED", "PROCESSING"}:
                        should_log = current_status == "PROCESSING"
                    else:
                        next_status = "FINAL_RECEIVED"
                elif event_type == "timeout":
                    if current_status in {
                        "LISTEN_TIMEOUT",
                        "FINAL_RECEIVED",
                        "PROCESSING",
                        "COMPLETED",
                    }:
                        pass
                    elif current_status in _ACTIVE_LISTEN_STATUSES:
                        next_status = "LISTEN_TIMEOUT"
                    else:
                        pass
                elif event_type in {"ended", "no_response"}:
                    if current_status in _PRE_FINAL_LISTEN_STATUSES:
                        next_status = "NO_RESPONSE"
                elif event_type == "partial":
                    if current_status == "LISTENING":
                        next_status = "PARTIAL"
                elif event_type == "error":
                    if current_status in _PRE_FINAL_LISTEN_STATUSES:
                        next_status = "RECOGNITION_ERROR"
                elif event_type == "retry":
                    if current_status in _PRE_FINAL_LISTEN_STATUSES:
                        next_status = "RETRY_REQUIRED"
                    elif current_status in {
                        "LISTEN_TIMEOUT",
                        "NO_RESPONSE",
                        "RECOGNITION_ERROR",
                        "RETRY_REQUIRED",
                    }:
                        should_log = True
                elif event_type in {"vad_speech_started", "vad_silence_started"}:
                    should_log = current_status in _ACTIVE_LISTEN_STATUSES
                elif event_type == "vad_segment_finalized":
                    if current_status in _ACTIVE_LISTEN_STATUSES:
                        next_status = "PROCESSING"

                if late:
                    if next_status is not None:
                        self._set_attempt(
                            connection,
                            listen_id=listen_id,
                            status=next_status,
                            client_turn_id=bound_client_id,
                            elapsed_ms=elapsed,
                            locale=locale,
                            implementation=implementation,
                            error_code=error_code,
                        )
                    late_error = True
                if next_status is not None:
                    self._set_attempt(
                        connection,
                        listen_id=listen_id,
                        status=next_status,
                        client_turn_id=bound_client_id,
                        elapsed_ms=elapsed,
                        locale=locale,
                        implementation=implementation,
                        error_code=error_code,
                    )
                    should_log = True
                elif event_type == "patient_listen_started" and current_status == "LISTENING":
                    should_log = False
                row = connection.execute(
                    "SELECT * FROM listening_attempts WHERE listen_id = ?",
                    (listen_id,),
                ).fetchone()

            if row is None:
                raise RuntimeError("listening attempt disappeared after event")
            payload = self._attempt_payload(row, event_type=event_type, duplicate=not should_log)

        if should_log:
            try:
                self.metrics.record_voice_event(
                    event_type=event_type,
                    call_id=call_id,
                    listen_id=listen_id,
                    client_turn_id=payload.get("client_turn_id"),
                    configured_timeout_ms=int(payload["configured_timeout_ms"]),
                    elapsed_ms=payload.get("elapsed_ms"),
                    locale=str(payload["locale"]),
                    implementation=str(payload["implementation"]),
                    status=str(payload["status"]),
                    error_code=payload.get("error_code"),
                    silence_timeout_ms=silence_timeout_ms,
                    sequence=sequence,
                )
            except Exception:
                pass
        if late_error:
            raise LateTranscriptError()
        return SerializableRecord(payload)

    def _claim_turn_attempt(
        self,
        call_id: str,
        *,
        listen_id: str | None,
        client_turn_id: str | None,
        elapsed_ms: Any | None,
    ) -> tuple[str | None, str | None, dict[str, Any] | None]:
        """Claim a final transcript before any model or clinical persistence work."""

        self._validate_public_id(listen_id, "listen_id")
        self._validate_public_id(client_turn_id, "client_turn_id")
        elapsed = self._validate_elapsed_ms(elapsed_ms)
        if listen_id is None and client_turn_id is None:
            return None, None, None
        if listen_id is None:
            listen_id = _new_id("listen")

        late_error = False
        with self.database.transaction() as connection:
            call_row = connection.execute(
                "SELECT status FROM calls WHERE id = ?",
                (call_id,),
            ).fetchone()
            if call_row is None:
                raise KeyError(f"unknown call: {call_id}")
            call_is_active = str(call_row["status"]) == "active"

            row = connection.execute(
                "SELECT * FROM listening_attempts WHERE listen_id = ?",
                (listen_id,),
            ).fetchone()
            existing_client = None
            if client_turn_id is not None:
                existing_client = connection.execute(
                    "SELECT * FROM listening_attempts WHERE client_turn_id = ?",
                    (client_turn_id,),
                ).fetchone()
                if existing_client is not None and str(existing_client["call_id"]) != str(call_id):
                    raise ListenEventError("client_turn_id_not_for_call")
            if row is not None and str(row["call_id"]) != str(call_id):
                raise ListenEventError("listen_id_not_for_call")
            if row is None and existing_client is not None:
                row = existing_client
                if str(row["listen_id"]) != listen_id:
                    if str(row["status"]) == "COMPLETED" and row["response_json"]:
                        stored = _json_loads(row["response_json"])
                        if isinstance(stored, dict):
                            return (
                                str(row["listen_id"]),
                                str(row["client_turn_id"]),
                                stored,
                            )
                    if str(row["status"]) == "LISTEN_TIMEOUT":
                        raise LateTranscriptError()
                    raise ListenEventError("client_turn_id_in_progress")

            if row is None:
                if not call_is_active:
                    raise ValueError(f"call is not active: {call_id}")
                self._insert_attempt(
                    connection,
                    call_id=call_id,
                    listen_id=listen_id,
                    client_turn_id=client_turn_id,
                    status="PROCESSING",
                    configured_timeout_ms=self.configured_timeout_ms,
                    elapsed_ms=elapsed,
                    locale=_VOICE_LOCALE,
                    implementation="SpeechRecognition",
                    error_code=None,
                )
            else:
                current_status = str(row["status"])
                stored_client_id = row["client_turn_id"]
                client_turn_id = client_turn_id or (
                    str(stored_client_id) if stored_client_id is not None else None
                )
                if current_status == "LISTEN_TIMEOUT":
                    raise LateTranscriptError()
                if stored_client_id is not None and client_turn_id != stored_client_id:
                    raise ListenEventError("client_turn_id_mismatch")
                if current_status == "COMPLETED" and row["response_json"]:
                    stored = _json_loads(row["response_json"])
                    if isinstance(stored, dict):
                        return str(row["listen_id"]), client_turn_id, stored
                if not call_is_active:
                    raise ValueError(f"call is not active: {call_id}")
                if current_status == "PROCESSING":
                    raise ListenEventError("turn_in_progress")
                if current_status in _TERMINAL_LISTEN_STATUSES:
                    raise LateTranscriptError()
                if elapsed is not None and elapsed > int(row["configured_timeout_ms"]):
                    self._set_attempt(
                        connection,
                        listen_id=listen_id,
                        status="LISTEN_TIMEOUT",
                        client_turn_id=client_turn_id,
                        elapsed_ms=elapsed,
                        locale=str(row["locale"]),
                        implementation=str(row["implementation"]),
                        error_code=None,
                    )
                    late_error = True
                self._set_attempt(
                    connection,
                    listen_id=listen_id,
                    status="PROCESSING" if not late_error else "LISTEN_TIMEOUT",
                    client_turn_id=client_turn_id,
                    elapsed_ms=elapsed,
                    locale=str(row["locale"]),
                    implementation=str(row["implementation"]),
                    error_code=None,
                )
        if late_error:
            raise LateTranscriptError()
        return listen_id, client_turn_id, None

    def record_turn(
        self,
        call_id: str,
        speaker: str,
        text: str,
        *,
        turn_id: str | None = None,
        turn_index: int | None = None,
        created_at: str | None = None,
        latency_ms: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        model_calls: int | None = None,
        rag_queries: int | None = None,
        sources: Iterable[Any] | None = None,
        triage: TriageResult | Mapping[str, Any] | None = None,
        triage_level: str | None = None,
        alert: bool | None = None,
        metrics: Mapping[str, Any] | None = None,
        speech_ended_at: Any | None = None,
        audio_started_at: Any | None = None,
        expected_corpus_revision: int | None = None,
    ) -> SerializableRecord:
        """Append a turn and its source links atomically."""

        if not isinstance(text, str):
            text = str(text)
        speaker_value = str(speaker or "unknown").strip().lower() or "unknown"
        metric_values = dict(metrics or {})
        if latency_ms is None:
            latency_ms = _float_or_none(metric_values.get("latency_ms"))
        if input_tokens is None:
            input_tokens = _integer(metric_values.get("input_tokens"), 0)
        if output_tokens is None:
            output_tokens = _integer(metric_values.get("output_tokens"), 0)
        if model_calls is None:
            model_calls = _integer(metric_values.get("model_calls"), 0)
        if rag_queries is None:
            rag_queries = _integer(metric_values.get("rag_queries"), 0)

        if triage is not None:
            if isinstance(triage, TriageResult):
                triage_level = triage.level
                if alert is None:
                    alert = triage.alert
            elif isinstance(triage, Mapping):
                triage_level = str(triage.get("level") or triage_level or "") or None
                if alert is None and triage.get("alert") is not None:
                    alert = bool(triage["alert"])
        normalized_turn_level = normalize_level(triage_level)
        timestamp = created_at or utc_now()
        turn_id = turn_id or _new_id("turn")
        persisted_source_ids: list[str] = []
        if isinstance(sources, Mapping):
            source_values = [sources]
        elif isinstance(sources, (str, bytes)):
            source_values = [sources]
        else:
            source_values = list(sources or ())

        with self.database.transaction() as connection:
            call_row = self._call_row_for_update(connection, call_id)
            if (
                expected_corpus_revision is not None
                and self.database.get_corpus_revision() != expected_corpus_revision
            ):
                raise CorpusRevisionChangedError()
            if turn_index is None:
                index_row = connection.execute(
                    "SELECT COALESCE(MAX(turn_index), -1) + 1 AS next_index "
                    "FROM turns WHERE call_id = ?",
                    (call_id,),
                ).fetchone()
                turn_index = _integer(index_row["next_index"], 0)
            if turn_index < 0:
                raise ValueError("turn_index must be non-negative")

            connection.execute(
                """
                INSERT INTO turns(
                    id, call_id, turn_index, speaker, text, created_at,
                    latency_ms, input_tokens, output_tokens, model_calls, rag_queries
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn_id,
                    call_id,
                    turn_index,
                    speaker_value,
                    text,
                    timestamp,
                    latency_ms,
                    input_tokens,
                    output_tokens,
                    max(0, _integer(model_calls)),
                    max(0, _integer(rag_queries)),
                ),
            )
            revision = self.database.get_corpus_revision()
            for source in source_values:
                source_value = self._source_payload(source, revision)
                # The existing schema intentionally protects document/chunk
                # references.  Keep the citation even when a caller supplies
                # a stale external identifier that is not in this database.
                if source_value["document_id"] is not None:
                    document_exists = connection.execute(
                        "SELECT 1 FROM documents WHERE id = ?",
                        (source_value["document_id"],),
                    ).fetchone()
                    if document_exists is None:
                        source_value["document_id"] = None
                if source_value["chunk_id"] is not None:
                    chunk_exists = connection.execute(
                        "SELECT 1 FROM chunks WHERE id = ?",
                        (source_value["chunk_id"],),
                    ).fetchone()
                    if chunk_exists is None:
                        source_value["chunk_id"] = None
                if source_value["document_id"] is not None:
                    document_snapshot = connection.execute(
                        "SELECT filename, sha256 FROM documents WHERE id = ?",
                        (source_value["document_id"],),
                    ).fetchone()
                    if document_snapshot is not None:
                        source_value["document_filename_snapshot"] = (
                            source_value["document_filename_snapshot"]
                            or document_snapshot["filename"]
                        )
                        source_value["document_sha256_snapshot"] = (
                            source_value["document_sha256_snapshot"] or document_snapshot["sha256"]
                        )
                if source_value["chunk_id"] is not None:
                    chunk_snapshot = connection.execute(
                        "SELECT chunk_index FROM chunks WHERE id = ?",
                        (source_value["chunk_id"],),
                    ).fetchone()
                    if chunk_snapshot is not None and source_value["chunk_index_snapshot"] is None:
                        source_value["chunk_index_snapshot"] = int(chunk_snapshot["chunk_index"])
                connection.execute(
                    """
                    INSERT INTO sources(
                        id, turn_id, document_id, chunk_id, page_number,
                        score, citation, corpus_revision, created_at,
                        document_filename_snapshot, document_sha256_snapshot,
                        chunk_index_snapshot
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_value["id"],
                        turn_id,
                        source_value["document_id"],
                        source_value["chunk_id"],
                        source_value["page_number"],
                        source_value["score"],
                        source_value["citation"],
                        source_value["corpus_revision"],
                        timestamp,
                        source_value["document_filename_snapshot"],
                        source_value["document_sha256_snapshot"],
                        source_value["chunk_index_snapshot"],
                    ),
                )
                persisted_source_ids.append(source_value["id"])

            previous_level = normalize_level(call_row["triage_level"])
            final_level = previous_level
            if normalized_turn_level is not None:
                final_level = highest_level((normalized_turn_level,), previous_level)
            final_alert = bool(call_row["alert"])
            if alert is not None:
                final_alert = final_alert or bool(alert)
            if final_level in {"red", "yellow"}:
                final_alert = True
            if final_level != previous_level or final_alert != bool(call_row["alert"]):
                connection.execute(
                    "UPDATE calls SET triage_level = ?, alert = ? WHERE id = ?",
                    (final_level, int(final_alert), call_id),
                )

        turn = self.get_turn(turn_id)
        if turn is None:
            raise RuntimeError("turn disappeared after insert")
        try:
            self.metrics.record_turn(
                call_id=call_id,
                turn_id=turn_id,
                speech_ended_at=speech_ended_at,
                audio_started_at=audio_started_at,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_calls=model_calls,
                rag_queries=rag_queries,
                source_ids=persisted_source_ids,
                model_version=metric_values.get("model_version"),
                created_at=timestamp,
            )
        except Exception:
            # Observability should not discard a persisted clinical conversation.
            pass
        return turn

    add_turn = record_turn

    def record_voice_timing(
        self,
        call_id: str,
        turn_id: str,
        *,
        speech_ended_at: Any,
        audio_started_at: Any,
    ) -> SerializableRecord:
        """Record browser audio timing for an existing agent turn only."""

        if self.get_call(call_id) is None:
            raise KeyError(f"unknown call: {call_id}")
        turn = self.get_turn(turn_id)
        if turn is None or str(turn.get("call_id")) != str(call_id):
            raise KeyError(f"unknown turn: {turn_id}")
        if str(turn.get("speaker") or "").casefold() not in {"agent", "assistant"}:
            raise ValueError("voice timing requires an agent turn")
        return SerializableRecord(
            self.metrics.record_voice_timing(
                call_id=call_id,
                turn_id=turn_id,
                speech_ended_at=speech_ended_at,
                audio_started_at=audio_started_at,
            )
        )

    record_voice_latency = record_voice_timing

    def get_turn(self, turn_id: str) -> SerializableRecord | None:
        row = self.database.execute(
            "SELECT turns.*, listening_attempts.listen_id, listening_attempts.client_turn_id "
            "FROM turns LEFT JOIN listening_attempts "
            "ON listening_attempts.patient_turn_id = turns.id "
            "OR listening_attempts.agent_turn_id = turns.id "
            "WHERE turns.id = ?",
            (turn_id,),
        ).fetchone()
        if row is None:
            return None
        result = SerializableRecord(
            {
                "id": str(row["id"]),
                "turn_id": str(row["id"]),
                "call_id": str(row["call_id"]),
                "turn_index": int(row["turn_index"]),
                "speaker": str(row["speaker"]),
                "text": str(row["text"]),
                "created_at": row["created_at"],
                "latency_ms": row["latency_ms"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "model_calls": int(row["model_calls"] or 0),
                "rag_queries": int(row["rag_queries"] or 0),
                "listen_id": row["listen_id"],
                "client_turn_id": row["client_turn_id"],
                "sources": self.get_sources(turn_id=turn_id),
            }
        )
        return result

    def list_turns(self, call_id: str) -> list[SerializableRecord]:
        rows = self.database.execute(
            "SELECT id FROM turns WHERE call_id = ? ORDER BY turn_index",
            (call_id,),
        ).fetchall()
        records: list[SerializableRecord] = []
        for row in rows:
            record = self.get_turn(str(row["id"]))
            if record is not None:
                records.append(record)
        return records

    get_turns = list_turns

    def get_sources(
        self,
        *,
        turn_id: str | None = None,
        call_id: str | None = None,
    ) -> list[SerializableRecord]:
        if turn_id is not None:
            rows = self.database.execute(
                "SELECT * FROM sources WHERE turn_id = ? ORDER BY created_at, id",
                (turn_id,),
            ).fetchall()
        elif call_id is not None:
            rows = self.database.execute(
                "SELECT sources.* FROM sources JOIN turns ON turns.id = sources.turn_id "
                "WHERE turns.call_id = ? ORDER BY sources.created_at, sources.id",
                (call_id,),
            ).fetchall()
        else:
            rows = self.database.execute("SELECT * FROM sources ORDER BY created_at, id").fetchall()
        return [
            SerializableRecord(
                {
                    "id": str(row["id"]),
                    "source_id": str(row["id"]),
                    "turn_id": row["turn_id"],
                    "document_id": row["document_id"],
                    "chunk_id": row["chunk_id"],
                    "document_filename_snapshot": row["document_filename_snapshot"],
                    "document_sha256_snapshot": row["document_sha256_snapshot"],
                    "chunk_index_snapshot": row["chunk_index_snapshot"],
                    "page_number": row["page_number"],
                    "score": row["score"],
                    "citation": str(row["citation"]),
                    "corpus_revision": int(row["corpus_revision"]),
                    "created_at": row["created_at"],
                }
            )
            for row in rows
        ]

    list_sources = get_sources

    @staticmethod
    def _default_next_steps(level: str) -> list[str]:
        if level == "red":
            return [
                "Buscar atencion de urgencias o contactar ahora al equipo clinico.",
                "No esperar una respuesta automatica para atender la senal de alarma.",
            ]
        if level == "yellow":
            return ["Contactar oportunamente al equipo clinico para indicaciones individualizadas."]
        if level == "unknown":
            return ["Aclarar los sintomas y completar la evaluacion con personal clinico."]
        return [
            "Continuar el seguimiento indicado por el equipo clinico y consultar si aparece "
            "una alarma."
        ]

    @staticmethod
    def _symptoms_from_turns(turns: Iterable[Mapping[str, Any]]) -> list[str]:
        return [
            str(turn.get("text") or "")
            for turn in turns
            if str(turn.get("speaker") or "").casefold() in {"patient", "paciente", "user"}
            and str(turn.get("text") or "").strip()
        ]

    def close_call(
        self,
        call_id: str,
        *,
        patient: Any | None = None,
        patient_id: str | None = None,
        procedure: str | None = None,
        symptoms: Iterable[Any] | Any | None = None,
        decision: str | None = None,
        sources: Iterable[Any] | None = None,
        alert: bool | None = None,
        next_steps: Iterable[Any] | None = None,
        summary: Mapping[str, Any] | None = None,
        ended_at: str | None = None,
    ) -> SerializableRecord:
        """Close a call with the required structured summary fields."""

        call = self.get_call(call_id)
        if call is None:
            raise KeyError(f"unknown call: {call_id}")
        supplied_summary = dict(summary or {})
        turns = self.list_turns(call_id)
        existing_level = normalize_level(call.get("triage_level"))
        requested_level = normalize_level(
            decision or supplied_summary.get("decision") or existing_level
        )
        if requested_level is None:
            requested_level = "unknown"
        final_level = highest_level(
            (requested_level,) if requested_level is not None else (),
            existing_level,
        )
        final_alert = bool(call.get("alert"))
        if alert is not None:
            final_alert = final_alert or bool(alert)
        if final_level in {"red", "yellow"}:
            final_alert = True
        final_patient = (
            patient_id
            if patient_id is not None
            else patient
            if patient is not None
            else supplied_summary.get("patient", call.get("patient_id"))
        )
        final_procedure = (
            procedure
            if procedure is not None
            else supplied_summary.get("procedure", call.get("procedure"))
        )

        if symptoms is None:
            supplied_symptoms = supplied_summary.get("symptoms")
            final_symptoms: list[Any] = supplied_symptoms or self._symptoms_from_turns(turns)
        elif isinstance(symptoms, str):
            final_symptoms = [symptoms]
        else:
            final_symptoms = list(symptoms)

        persisted_sources = self.get_sources(call_id=call_id)
        if sources is None:
            final_sources: list[Any] = [dict(source) for source in persisted_sources]
        elif isinstance(sources, Mapping) or isinstance(sources, (str, bytes)):
            final_sources = [_as_dict(sources)]
        else:
            final_sources = [_as_dict(source) for source in sources]
        final_steps = (
            list(next_steps)
            if next_steps is not None
            else list(supplied_summary.get("next_steps") or self._default_next_steps(final_level))
        )
        final_summary = {
            "patient": final_patient,
            "patient_id": final_patient,
            "procedure": final_procedure,
            "symptoms": final_symptoms,
            "decision": final_level,
            "triage_level": final_level,
            "sources": final_sources,
            "alert": final_alert,
            "next_steps": final_steps,
        }
        # Preserve explicitly supplied extension fields without allowing them
        # to remove a required field.
        for key, value in supplied_summary.items():
            if key not in final_summary:
                final_summary[key] = value

        timestamp = ended_at or utc_now()
        summary_json = json.dumps(final_summary, ensure_ascii=False, sort_keys=True)
        with self.database.transaction() as connection:
            pending_attempt = connection.execute(
                "SELECT 1 FROM listening_attempts "
                "WHERE call_id = ? AND status IN ('PROCESSING', 'FINAL_RECEIVED') LIMIT 1",
                (call_id,),
            ).fetchone()
            if pending_attempt is not None:
                raise ValueError("turn is in progress")
            connection.execute(
                "UPDATE calls SET status = 'closed', ended_at = ?, summary_json = ?, "
                "triage_level = ?, alert = ? WHERE id = ? AND status = 'active'",
                (timestamp, summary_json, final_level, int(final_alert), call_id),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValueError(f"call is not active: {call_id}")
            self.database.record_audit(
                entity_type="call",
                entity_id=call_id,
                action="close",
                details={
                    "triage_level": final_level,
                    "alert": final_alert,
                    "source_count": len(final_sources),
                },
                connection=connection,
            )
        closed = self.get_call(call_id)
        if closed is None:
            raise RuntimeError("call disappeared after close")
        return closed

    end_call = close_call
    close = close_call

    def summary(self, call_id: str) -> dict[str, Any] | None:
        call = self.get_call(call_id)
        if call is None:
            return None
        value = call.get("summary")
        return dict(value) if isinstance(value, Mapping) else None

    @staticmethod
    def _corpus_changed_response(
        triage: TriageResult,
        metrics: Mapping[str, Any],
    ) -> dict[str, Any]:
        text = (
            "El conocimiento disponible cambio durante la consulta. "
            "No puedo responder con seguridad; intente de nuevo."
        )
        voice_code = {
            "red": "TRIAGE_RED",
            "yellow": "TRIAGE_YELLOW",
        }.get(triage.level, "CORPUS_CHANGED")
        return {
            "text": text,
            "answer": text,
            "response": text,
            "patient_text": voice_message(voice_code),
            "voice_text": voice_message(voice_code),
            "display_text": voice_message(voice_code),
            "source_display": [],
            "internal_reason": "corpus_changed",
            "grounded": False,
            "abstained": True,
            "reason": "corpus_changed",
            "sources": [],
            "alert": triage.alert,
            "level": triage.level,
            "metrics": dict(metrics),
        }

    def _complete_listen_attempt(
        self,
        *,
        listen_id: str,
        patient_turn_id: str,
        agent_turn_id: str,
        response: Mapping[str, Any],
    ) -> None:
        response_json = json.dumps(dict(response), ensure_ascii=False, default=str, sort_keys=True)
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT status FROM listening_attempts WHERE listen_id = ?",
                (listen_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("listening attempt disappeared before completion")
            if str(row["status"]) not in {"PROCESSING", "FINAL_RECEIVED"}:
                raise ListenEventError("turn_state_changed")
            connection.execute(
                "UPDATE listening_attempts SET status = 'COMPLETED', patient_turn_id = ?, "
                "agent_turn_id = ?, response_json = ?, updated_at = ? WHERE listen_id = ?",
                (patient_turn_id, agent_turn_id, response_json, utc_now(), listen_id),
            )

    def handle_turn(
        self,
        call_id: str,
        text: str,
        *,
        agent: Any | None = None,
        patient_speaker: str = "patient",
        agent_speaker: str = "agent",
        history: Iterable[Any] | None = None,
        client_turn_id: str | None = None,
        listen_id: str | None = None,
        elapsed_ms: Any | None = None,
    ) -> SerializableRecord:
        """Run an agent for one patient turn and persist both sides."""

        active_agent = agent or self.agent
        call = self.get_call(call_id)
        if call is None:
            raise KeyError(f"unknown call: {call_id}")

        claimed_listen_id, claimed_client_turn_id, duplicate_response = self._claim_turn_attempt(
            call_id,
            listen_id=listen_id,
            client_turn_id=client_turn_id,
            elapsed_ms=elapsed_ms,
        )
        if duplicate_response is not None:
            duplicate_response = dict(duplicate_response)
            duplicate_response["duplicate"] = True
            if claimed_listen_id is not None:
                duplicate_response.setdefault("listen_id", claimed_listen_id)
            if claimed_client_turn_id is not None:
                duplicate_response.setdefault("client_turn_id", claimed_client_turn_id)
            return SerializableRecord(duplicate_response)
        if active_agent is None:
            if claimed_listen_id is not None:
                with self.database.transaction() as connection:
                    connection.execute(
                        "UPDATE listening_attempts SET status = 'FINAL_RECEIVED', updated_at = ? "
                        "WHERE listen_id = ? AND status = 'PROCESSING'",
                        (utc_now(), claimed_listen_id),
                    )
            raise ValueError("an AgentService is required to handle a turn")

        from .triage import classify_triage

        triage = classify_triage(text, previous_level=call.get("triage_level"))
        patient_turn = self.record_turn(
            call_id,
            patient_speaker,
            text,
            triage=triage,
        )
        try:
            responder = getattr(active_agent, "respond", None) or getattr(
                active_agent, "answer", None
            )
            if not callable(responder):
                raise TypeError("agent has no respond/answer method")
            try:
                response = responder(
                    text,
                    history=history,
                    previous_level=call.get("triage_level"),
                    triage_result=triage,
                    call_id=call_id,
                )
            except TypeError:
                response = responder(text)
        except Exception as exc:
            # Keep the patient turn persisted, but do not fabricate an answer.
            safe_voice = voice_message(
                "TRIAGE_RED"
                if triage.level == "red"
                else "TRIAGE_YELLOW"
                if triage.level == "yellow"
                else "AGENT_ERROR"
            )
            safe_display = display_message(
                "ALERT_RED_UI"
                if triage.level == "red"
                else "ALERT_YELLOW_UI"
                if triage.level == "yellow"
                else "AGENT_ERROR"
            )
            response = {
                "text": "No pude generar una respuesta segura. Contacte a su equipo clinico.",
                "answer": "No pude generar una respuesta segura. Contacte a su equipo clinico.",
                "patient_text": safe_voice,
                "voice_text": safe_voice,
                "display_text": safe_voice,
                "source_display": [],
                "internal_reason": "agent_error",
                "abstained": True,
                "alert": triage.alert,
                "level": triage.level,
                "sources": [],
                "metrics": {
                    "latency_ms": None,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "model_calls": 0,
                    "rag_queries": 0,
                },
                "error": str(exc),
            }
        if isinstance(response, Mapping):
            response_data = dict(response)
        else:
            response_data = {"text": str(response), "answer": str(response), "sources": []}
        response_text = str(response_data.get("text") or response_data.get("answer") or "")
        patient_text = str(
            response_data.get("patient_text")
            or response_data.get("voice_text")
            or response_data.get("display_text")
            or response_text
        ).strip()
        response_data["patient_text"] = patient_text
        response_data["voice_text"] = patient_text
        response_data["display_text"] = patient_text
        response_metrics = response_data.get("metrics")
        if not isinstance(response_metrics, Mapping):
            response_metrics = response_data

        source_values = response_data.get("sources") or ()
        if isinstance(source_values, Mapping) or isinstance(source_values, (str, bytes)):
            source_values = [source_values]
        else:
            source_values = list(source_values)
        source_revisions: list[int] = []
        revision_fields = 0
        for source in source_values:
            source_value = _as_dict(source)
            if "corpus_revision" not in source_value:
                continue
            revision_fields += 1
            try:
                source_revisions.append(int(source_value["corpus_revision"]))
            except (TypeError, ValueError):
                source_revisions.append(-1)
        expected_revision = (
            source_revisions[0]
            if revision_fields == len(source_values)
            and source_revisions
            and len(set(source_revisions)) == 1
            else None
        )
        stale_evidence = bool(source_values) and (
            revision_fields > 0
            and (
                expected_revision is None
                or self.database.get_corpus_revision() != expected_revision
            )
        )
        if stale_evidence:
            response_data = self._corpus_changed_response(triage, response_metrics)
            response_text = response_data["text"]
            response_metrics = response_data["metrics"]
            source_values = []
            expected_revision = None
        try:
            agent_turn = self.record_turn(
                call_id,
                agent_speaker,
                response_text,
                sources=source_values,
                metrics=response_metrics,
                triage=triage,
                expected_corpus_revision=expected_revision,
            )
        except CorpusRevisionChangedError:
            response_data = self._corpus_changed_response(triage, response_metrics)
            response_text = response_data["text"]
            agent_turn = self.record_turn(
                call_id,
                agent_speaker,
                response_text,
                sources=(),
                metrics=response_data["metrics"],
                triage=triage,
            )
        response_data.update(
            {
                "call_id": call_id,
                "patient_turn_id": patient_turn["id"],
                "agent_turn_id": agent_turn["id"],
                "triage": triage.to_dict(),
                "duplicate": False,
            }
        )
        if claimed_listen_id is not None:
            response_data["listen_id"] = claimed_listen_id
        if claimed_client_turn_id is not None:
            response_data["client_turn_id"] = claimed_client_turn_id
        if claimed_listen_id is not None:
            self._complete_listen_attempt(
                listen_id=claimed_listen_id,
                patient_turn_id=str(patient_turn["id"]),
                agent_turn_id=str(agent_turn["id"]),
                response=response_data,
            )
        return SerializableRecord(response_data)

    process_turn = handle_turn
    respond = handle_turn


def create_call(
    database: Database,
    patient_id: str | None = None,
    procedure: str | None = None,
    **kwargs: Any,
) -> SerializableRecord:
    return CallService(database).start_call(patient_id, procedure, **kwargs)


def record_turn(
    database: Database,
    call_id: str,
    speaker: str,
    text: str,
    **kwargs: Any,
) -> SerializableRecord:
    return CallService(database).record_turn(call_id, speaker, text, **kwargs)


def close_call(database: Database, call_id: str, **kwargs: Any) -> SerializableRecord:
    return CallService(database).close_call(call_id, **kwargs)


__all__ = [
    "CallService",
    "CorpusRevisionChangedError",
    "LateTranscriptError",
    "ListenEventError",
    "SerializableRecord",
    "close_call",
    "create_call",
    "record_turn",
]
