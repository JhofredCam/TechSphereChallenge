# Tareas: Migracion RAG de produccion

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
