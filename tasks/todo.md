# Tareas: Migracion RAG de produccion

## Addendum: CALL-VOICE-026

- [x] **CALL-VOICE-T01 Contrato de timeout continuo**
  - Aceptacion: la spec define la carrera tardia y conserva `409 late_transcript` del backend.
  - Verificar: revisar `specs/26_voice_timeout_final_race_specification.md`.
  - Archivos: `specs/26_voice_timeout_final_race_specification.md`, `tasks/plan.md`.
- [x] **CALL-VOICE-T02 Guarda frontend**
  - Aceptacion: resultado posterior al limite registra solo `timeout`, no registra `final` y no
    llama `/turns`.
  - Verificar: `python -m pytest tests/test_call_ui_contracts.py -q --basetemp .pytest-tmp/voice-ui`.
  - Archivos: `app/web/app.js`, `tests/test_call_ui_contracts.py`.
- [x] **CALL-VOICE-T03 Regresion y cierre**
  - Aceptacion: camino dentro de plazo y backend tardio conservan su contrato; suite completa y
    checks pasan; bitacora sincronizada.
  - Verificar: `python -m pytest -q --basetemp .pytest-tmp/voice-timeout-race-full`.
  - Archivos: `tests/test_timeout.py`, `tests/test_voice_events.py`, `readme/06_bitacora_de_sesiones/`.

## Addendum: AGENT-RECOVERY-025

- [x] **AGENT-RECOVERY-T01 Configuracion LLM local**
  - Aceptacion: `.env` se lee solo en la instancia por defecto, el entorno del proceso gana y
    `Settings` explícito no activa red.
  - Verificar: `python -m pytest tests/test_config_contracts.py -q --basetemp .pytest-tmp/agent-config`.
  - Archivos: `app/config.py`, `tests/test_config_contracts.py`.
- [x] **AGENT-RECOVERY-T02 Inyeccion y health**
  - Aceptacion: agente/Whisper reciben la configuracion cargada y `/health` distingue Groq de
    fallback sin secretos.
  - Verificar: `python -m pytest tests/test_api.py -q --basetemp .pytest-tmp/agent-api`.
  - Archivos: `app/main.py`, `app/services/voice.py`, `tests/test_api.py`.
- [x] **AGENT-RECOVERY-T03 Respuesta segura**
  - Aceptacion: ausencia, error, timeout, JSON vacío o salida insegura del modelo nunca dejan
    `patient_text` vacío ni convierten el turno en 500.
  - Verificar: `python -m pytest tests/test_agent.py -q --basetemp .pytest-tmp/agent-agent`.
  - Archivos: `app/services/agent.py`, `tests/test_agent.py`.
- [x] **AGENT-RECOVERY-T04 Cierre y evidencia**
  - Aceptacion: suite completa, Ruff, Node check, spec y bitácora sincronizados; sin secretos.
  - Verificar: `python -m pytest -q --basetemp .pytest-tmp/agent-full`.
  - Archivos: `specs/25_agent_response_recovery_specification.md`, `readme/06_bitacora_de_sesiones/`.

Las tareas se ejecutan en orden de dependencia. Cada tarea debe actualizar su spec antes de
implementar una decision nueva y conservar un comando de verificacion. Ninguna casilla representa
una capacidad ya implementada en el checkout.

## Contratos y configuracion

- [ ] **RAG-T01 Configuracion tipada y perfiles**
  - Aceptacion: `RAG-ENV-001` tiene parser fail-fast, perfiles local/staging/production y dump redacted.
  - Verificar: `python -m pytest tests/test_config_contracts.py -q --basetemp <temp>/rag-config`.
  - Archivos: `app/config.py`, `tests/test_config_contracts.py`, `.env.example`.

- [ ] **RAG-T02 Dependencias fijadas**
  - Aceptacion: Chroma, LangChain core/integracion, provider elegido y herramientas de test tienen
    versiones compatibles y no rompen setup local.
  - Verificar: `python -m pip install -r requirements.txt` y `python -m pytest -q --basetemp <temp>/deps`.
  - Archivos: `requirements.txt`, `requirements-dev.txt`, `README.md`.

- [ ] **RAG-T03 Protocolos estables**
  - Aceptacion: `VectorStore`, `EmbeddingProvider`, `DocumentLoader`, `IndexManifest` y
    `SearchResult` tienen interfaces tipadas sin romper FTS5.
  - Verificar: `python -m pytest tests/test_schema_contracts.py tests/test_vector_store.py -q --basetemp <temp>/protocols`.
  - Archivos: `app/schemas.py`, `app/services/vector_store.py`, `app/services/embeddings.py`, `app/services/loaders.py`.

## Chroma y lifecycle

- [ ] **RAG-T04 Metadata de indice y migracion SQLite**
  - Aceptacion: schema versionado guarda manifest, estado, version activa y lag sin alterar snapshots.
  - Verificar: `python -m pytest tests/test_database.py tests/test_rag_operations.py -q --basetemp <temp>/index-meta`.
  - Archivos: `app/database.py`, `app/services/index_manager.py`, `tests/test_database.py`.

- [ ] **RAG-T05 Backfill Chroma idempotente**
  - Aceptacion: build crea coleccion versionada, IDs deterministas y metadata completa; segunda
    ejecucion no duplica vectores.
  - Verificar: `python -m scripts.build_rag_index --index-version <version> --data-dir <temp>/backfill`.
  - Archivos: `app/services/vector_store.py`, `scripts/build_rag_index.py`, `tests/test_vector_store.py`.

- [ ] **RAG-T06 Retrieval con hydration SQLite**
  - Aceptacion: Chroma devuelve candidatos, SQLite autoriza, score se convierte y `SearchResult`
    mantiene cita/revision.
  - Verificar: `python -m pytest tests/test_rag_consistency.py tests/test_agent.py -q --basetemp <temp>/retrieval`.
  - Archivos: `app/services/rag.py`, `app/services/vector_store.py`, `tests/test_rag_consistency.py`.

- [ ] **RAG-T07 Lifecycle admin dual-write**
  - Aceptacion: upload, disable, enable y delete sincronizan FTS5/Chroma, no fugan y funcionan sin reinicio.
  - Verificar: `python -m pytest tests/test_admin_lifecycle.py tests/test_live_knowledge.py -q --basetemp <temp>/dual-write`.
  - Archivos: `app/services/documents.py`, `app/database.py`, `tests/test_live_knowledge.py`.

- [ ] **RAG-T08 Reconciliacion y fallos parciales**
  - Aceptacion: detecta stale vectors, ausentes, huerfanos, dimension incorrecta y repara de forma auditable.
  - Verificar: `python -m scripts.reconcile_rag_index --dry-run` y `python -m pytest tests/test_rag_operations.py -q`.
  - Archivos: `scripts/reconcile_rag_index.py`, `app/services/index_manager.py`, `tests/test_rag_operations.py`.

## Benchmark

- [ ] **RAG-T09 Snapshot de evaluacion y qrels**
  - Aceptacion: queries/qrels versionados, separados por documento, sin PII, labels prohibidos o mezcla de capas.
  - Verificar: `python -m scripts.prepare_rag_eval --output <temp>/qrels.jsonl` y tests de contratos.
  - Archivos: `scripts/prepare_rag_eval.py`, `benchmarks/rag/qrels.jsonl`, `tests/test_benchmark_contracts.py`.

- [ ] **RAG-T10 Runner de matriz**
  - Aceptacion: compara C0/C1/C2, providers/modelos y FTS5 con warmups, repeticiones, concurrencia y manifest.
  - Verificar: `python -m scripts.benchmark_rag --matrix configs/rag_benchmark.yaml --repetitions 5 --output <temp>/results.json`.
  - Archivos: `scripts/benchmark_rag.py`, `configs/rag_benchmark.yaml`, `tests/test_benchmark_contracts.py`.

- [ ] **RAG-T11 Decision de candidato**
  - Aceptacion: reporte calcula recall, precision, hit, MRR/nDCG, context precision, citas, abstencion,
    latencias y memoria; aplica gates sin fabricar valores.
  - Verificar: `python -m scripts.compare_rag_runs --baseline <temp>/fts5.json --candidate <temp>/results.json`.
  - Archivos: `scripts/compare_rag_runs.py`, `benchmarks/rag/README.md`, `readme/04_metricas_y_evidencia.md`.

## LangChain y prompt

- [ ] **RAG-T12 Loaders y documentos LangChain**
  - Aceptacion: PDF/TXT/MD conservan pagina, offsets, OCR, hash y metadata al adaptarse a `Document`.
  - Verificar: `python -m pytest tests/test_loader_contracts.py tests/test_ingestion.py -q --basetemp <temp>/loaders`.
  - Archivos: `app/services/loaders.py`, `app/services/ingestion.py`, `tests/test_loader_contracts.py`.

- [ ] **RAG-T13 Runnables y retriever visible**
  - Aceptacion: nodos de normalize/triage/retrieve/hydrate/context/prompt/validate tienen timeouts y metricas.
  - Verificar: `python -m pytest tests/test_rag_chain.py tests/test_rag_consistency.py -q --basetemp <temp>/chain`.
  - Archivos: `app/services/rag_chain.py`, `app/services/rag.py`, `tests/test_rag_chain.py`.

- [ ] **RAG-T14 Prompt y salida segura**
  - Aceptacion: prompt versionado, idioma, cita, abstencion, injection, dosis/diagnostico y triage seguro.
  - Verificar: `python -m pytest tests/test_prompt_contracts.py tests/test_agent.py tests/test_triage.py -q --basetemp <temp>/prompt`.
  - Archivos: `app/services/prompts.py`, `app/services/agent.py`, `tests/test_prompt_contracts.py`.

## Observabilidad y operaciones

- [ ] **RAG-T15 Spans y redaction**
  - Aceptacion: retrieval, embedding, Chroma, fusion, LLM, STT/TTS y validacion tienen spans redacted; exporter fail-open.
  - Verificar: `python -m pytest tests/test_observability_contracts.py tests/test_metrics.py -q --basetemp <temp>/observability`.
  - Archivos: `app/services/observability.py`, `app/services/metrics.py`, `tests/test_observability_contracts.py`.

- [ ] **RAG-T16 Health y metricas de RAG**
  - Aceptacion: health y `/api/metrics` muestran backend/version/lag/latencias sin secrets y conservan campos existentes.
  - Verificar: `python -m pytest tests/test_api.py tests/test_metrics.py -q --basetemp <temp>/health`.
  - Archivos: `app/main.py`, `app/services/metrics.py`, `tests/test_http_contracts.py`.

- [ ] **RAG-T17 Promotion/canary/rollback**
  - Aceptacion: build, validate, shadow, canary, promotion y rollback a FTS5/version previa son idempotentes y auditables.
  - Verificar: `python -m pytest tests/test_rag_operations.py -q --basetemp <temp>/operations`.
  - Archivos: `app/services/index_manager.py`, `scripts/promote_rag_index.py`, `tests/test_rag_operations.py`.

- [ ] **RAG-T18 Backup y restauracion**
  - Aceptacion: SQLite, Chroma, manifest, uploads y events se restauran en temporal sin reintroducir snapshots.
  - Verificar: `python -m scripts.restore_rag_backup --source <backup> --data-dir <temp>/restore`.
  - Archivos: `scripts/backup_rag.py`, `scripts/restore_rag_backup.py`, `tests/test_rag_operations.py`.

## Propagacion y evidencia

- [ ] **RAG-T19 Diagrama y specs previas**
  - Aceptacion: Specs 00, 01, 02, 04, 05, 06, 07, 10 y 11 no contradicen Chroma/configuracion/tracing y
    la matriz `TRZ-*` apunta a los nuevos contratos.
  - Verificar: `python -m pytest tests/test_structure.py -q` y revision de enlaces Markdown.
  - Archivos: `specs/00_mvp_specification.md`, `specs/04_admin_document_lifecycle_specification.md`, `specs/06_system_flow_diagram_specification.md`, `specs/07_testing_unit_integration_specification.md`.

- [ ] **RAG-T20 CRISP-DM y arquitectura publicada**
  - Aceptacion: data preparation/modeling/evaluation/deployment, `docs/arquitectura.md` y vista formal
    reflejan baseline/target y estados honestos.
  - Verificar: `python -m scripts.validate_dataset` y `git diff --check`.
  - Archivos: `mvp/crisp-dm/03_data_preparation/README.md`, `mvp/crisp-dm/04_modeling/README.md`, `mvp/crisp-dm/05_evaluation/README.md`, `docs/arquitectura.md`.

- [ ] **RAG-T21 README, setup, demo e informe**
  - Aceptacion: setup, variables, comandos, modelo exacto, benchmark, metricas, rollback y G2-G5 estan sincronizados.
  - Verificar: ejecutar comandos del README en entorno limpio y completar evidencia manual.
  - Archivos: `README.md`, `readme/02_setup_local.md`, `readme/03_demo_funcional.md`, `docs/informe-final.md`.

- [ ] **RAG-T22 Cierre de gates**
  - Aceptacion: cada gate tiene artefacto fechado y estado `TESTED`, `MANUAL_PENDING` o `FAILED`; no se inventan P50/P95/costo.
  - Verificar: `python -m pytest -q --basetemp <temp>/final`, smoke G4 y G5 externo.
  - Archivos: `readme/04_metricas_y_evidencia.md`, `mvp/deliverables/03_final_report/README.md`, `docs/informe-final.md`.

## Logging propio y trazabilidad

- [ ] **LOG-T01 Contrato y configuracion del logger**
  - Aceptacion: `AppLogger` implementa niveles `DEBUG/INFO/WARN/ERROR`, contexto, JSONL,
    consola opcional, rotacion y variables `APP_LOG_*` validadas.
  - Verificar: `python -m pytest tests/test_logger.py -q --basetemp <temp>/logger`.
  - Archivos: `app/services/logger.py`, `app/config.py`, `.env.example`, `tests/test_logger.py`.

- [ ] **LOG-T02 Redaccion y errores fail-open**
  - Aceptacion: stack traces completos redacted, secretos/PII/audio/transcript fuera del log,
    exporter/sink fallido no bloquea la persistencia clinica y deja `observability_degraded`.
  - Verificar: `python -m pytest tests/test_logger.py tests/test_observability_contracts.py -q --basetemp <temp>/logging`.
  - Archivos: `app/services/logger.py`, `app/services/observability.py`, `tests/`.

- [ ] **LOG-T03 Instrumentacion end-to-end**
  - Aceptacion: startup, API, admin, llamadas, estados VAD/audio, RAG, agente, ingestion y
    excepciones comparten correlacion sin duplicar `events.jsonl`.
  - Verificar: integracion HTTP y conciliacion de `data/app.log.jsonl`/`data/events.jsonl`.
  - Archivos: `app/main.py`, `app/bootstrap.py`, `app/services/`, `tests/`.

## Suite fail-detect

- [ ] **TEST-T01 Unitarias deterministas**
  - Aceptacion: logger, transformadores, ingestion, triaje, VAD, RAG, metricas y render
    contracts fallan ante regresiones de redaccion, cita, timeout o DOM seguro.
  - Verificar: `python -m pytest tests/test_logger.py tests/test_vad.py tests/test_metrics.py tests/test_rendering_contracts.py -q --basetemp <temp>/unit`.
  - Archivos: `tests/test_logger.py`, `tests/test_vad.py`, `tests/test_metrics.py`, `tests/test_rendering_contracts.py`.

- [ ] **TEST-T02 Integracion de llamada, audio, admin y RAG**
  - Aceptacion: `TestClient` con SQLite/FTS5 real prueba llamada, triaje sticky, resumen,
    eventos VAD, timeout/idempotencia, upload/disable/enable/delete y aprender/olvidar.
  - Verificar: `python -m pytest tests/test_call_flow_integration.py tests/test_audio_vad_integration.py tests/test_data_flow_integration.py tests/test_live_knowledge.py -q --basetemp <temp>/integration`.
  - Archivos: `tests/test_call_flow_integration.py`, `tests/test_audio_vad_integration.py`, `tests/test_data_flow_integration.py`, `tests/`.

- [ ] **TEST-T03 Suite completa y frontera manual**
  - Aceptacion: suite completa, coverage por ramas >=80%, Ruff y Node check pasan; G2/G4/G5
    quedan clasificados honestamente como automatizados o `MANUAL_PENDING`.
  - Verificar: `python -m pytest -q --basetemp <temp>/full --cov=app --cov=scripts --cov-branch --cov-fail-under=80`, `ruff check app scripts tests` y `node --check app/web/app.js app/web/voice-loop.js`.
  - Archivos: `pyproject.toml`, `tests/`, `readme/04_metricas_y_evidencia.md`, `docs/informe-final.md`, `readme/06_bitacora_de_sesiones/`.
