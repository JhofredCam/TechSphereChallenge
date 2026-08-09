# Tareas ejecutables del MVP

Esta lista conserva el backlog original del MVP. Sus casillas no sustituyen el estado de
implementacion ni la evidencia descritos en `mvp/`, `README.md` y `docs/informe-final.md`; una
tarea puede permanecer sin marcar aunque exista una implementacion local verificada. Las tareas
03-07 del siguiente corte estan marcadas por su estado aplicado.

- [ ] Crear configuracion y esquema SQLite
  - Aceptacion: `init_database()` crea tablas, FTS5, metadata de indice y directorios locales sin secretos.
  - Verificar: `python -m pytest tests/test_database.py tests/test_config_contracts.py -q`.
  - Archivos: `app/config.py`, `app/database.py`, `app/schemas.py`.

- [ ] Implementar ingestion y ciclo de vida documental
  - Aceptacion: PDF/TXT/MD se procesan por pagina, se generan chunks y se registra
    `available`, `needs_ocr` o `error`.
  - Verificar: `python -m pytest tests/test_ingestion.py -q`.
  - Archivos: `app/services/ingestion.py`, `app/services/documents.py`.

- [ ] Implementar recuperacion y trazabilidad
  - Aceptacion: cada resultado contiene documento, pagina, chunk, cita y revision del corpus;
    borrar elimina los resultados futuros en FTS5 y Chroma.
  - Verificar: `python -m pytest tests/test_live_knowledge.py tests/test_rag_consistency.py -q`.
  - Archivos: `app/services/rag.py`, `app/services/vector_store.py`, `app/database.py`.

- [ ] Implementar dataset foundation
  - Aceptacion: valida hojas, encabezados, filas, JSON embebido y joins sin mezclar capas.
  - Verificar: `python -m scripts.validate_dataset`.
  - Archivos: `app/dataset.py`, `scripts/validate_dataset.py`.

- [ ] Implementar triaje, llamada y resumen
  - Aceptacion: rojo no baja, amarillo crea alerta, ambiguo pregunta y cierre persiste
    resumen estructurado.
  - Verificar: `python -m pytest tests/test_triage.py tests/test_calls.py -q`.
  - Archivos: `app/services/triage.py`, `app/services/calls.py`.

- [ ] Integrar respuesta grounded y metricas
  - Aceptacion: modo Groq usa modelo permitido configurado; sin fuente hay abstencion; cada
    turno registra latencia, tokens, invocaciones y consultas RAG.
  - Verificar: `python -m pytest tests/test_agent.py tests/test_metrics.py -q`.
  - Archivos: `app/services/agent.py`, `app/services/metrics.py`.

- [ ] Exponer API y superficies web
  - Aceptacion: `/admin` soporta upload/list/delete y `/call` soporta microfono, respuesta
    hablada y fallback textual.
  - Verificar: `python -m pytest tests/test_api.py -q` y smoke manual.
  - Archivos: `app/main.py`, `app/web/`.

- [ ] Cerrar bootstrap, documentacion y evidencia
  - Aceptacion: README reproduce setup en <=15 minutos, incluye modelo, diagrama, metricas,
    informe y checklist G1-G5.
  - Verificar: ejecutar todos los comandos del README desde un entorno limpio.
  - Archivos: `README.md`, `readme/`, `mvp/`, `docs/arquitectura.md`, `docs/informe-final.md`.

## Tareas de migracion RAG de produccion

La lista detallada, con tareas de una sola sesion, esta en [`tasks/todo.md`](../tasks/todo.md). Este
resumen conserva el backlog historico y fija la secuencia normativa del upgrade:

- [ ] Configuracion externa y `.env.example` completo
  - Aceptacion: chunking, embeddings, Chroma, retrieval y LangSmith se validan por entorno.
  - Verificar: `python -m pytest tests/test_config_contracts.py -q --basetemp <temp>/rag-config`.
  - Archivos: `app/config.py`, `.env.example`, `tests/test_config_contracts.py`.

- [ ] Contratos de loader, embeddings, vector store y manifest
  - Aceptacion: FTS5 mantiene `SearchResult`; Chroma y providers se inyectan sin objetos externos en API.
  - Verificar: `python -m pytest tests/test_schema_contracts.py tests/test_vector_store.py -q`.
  - Archivos: `app/schemas.py`, `app/services/loaders.py`, `app/services/embeddings.py`, `app/services/vector_store.py`.

- [ ] ChromaDB dual-write, hydration, reconciliacion y delete seguro
  - Aceptacion: upload/disable/enable/delete sin reinicio, cero fugas y rollback FTS5.
  - Verificar: `python -m pytest tests/test_rag_consistency.py tests/test_live_knowledge.py tests/test_rag_operations.py -q`.
  - Archivos: `app/services/rag.py`, `app/services/documents.py`, `app/services/index_manager.py`, `tests/`.

- [ ] Benchmark experimental de chunkers y embeddings
  - Aceptacion: qrels, recall, precision, hit rate, MRR/nDCG, context precision, citas,
    abstencion, latencias y memoria con decision contra FTS5.
  - Verificar: `python -m scripts.benchmark_rag --matrix configs/rag_benchmark.yaml --gate --output <temp>/rag-results.json`.
  - Archivos: `scripts/prepare_rag_eval.py`, `scripts/benchmark_rag.py`, `scripts/compare_rag_runs.py`, `benchmarks/`.

- [ ] LangChain, prompt y validacion de respuesta
  - Aceptacion: loader/runnable/prompt son visibles; triaje, citas, abstencion y seguridad siguen fuera del framework.
  - Verificar: `python -m pytest tests/test_loader_contracts.py tests/test_rag_chain.py tests/test_prompt_contracts.py -q`.
  - Archivos: `app/services/rag_chain.py`, `app/services/prompts.py`, `app/services/agent.py`, `tests/`.

- [ ] LangSmith redacted y observabilidad por nodo
  - Aceptacion: tracing opcional, fail-open, sin PII/contenido por defecto y metricas conciliables con JSONL.
  - Verificar: `python -m pytest tests/test_observability_contracts.py tests/test_metrics.py -q`.
  - Archivos: `app/services/observability.py`, `app/services/metrics.py`, `tests/test_observability_contracts.py`.

- [ ] Rollout, rollback, backup y propagacion documental
  - Aceptacion: shadow/canary/promotion/rollback, README, diagrama, CRISP-DM, informe y specs 06/07 sincronizados.
  - Verificar: `python -m pytest -q --basetemp <temp>/rag-final`, `git diff --check` y smoke manual G2-G5.
  - Archivos: `scripts/`, `specs/`, `README.md`, `docs/`, `mvp/`, `readme/`.

## Tareas del siguiente corte

- [x] Reorganizar el paquete de entregables bajo `mvp/`
  - Aceptacion: las seis fases quedan previstas bajo `mvp/crisp-dm/`, los cuatro entregables
    bajo `mvp/deliverables/` y no se copian `dataset/` ni `docs/`.
  - Verificar: revisar ownership, enlaces relativos y ausencia de rutas prohibidas; no ejecutar
    una migracion en esta sesion de planificacion.
  - Archivos: `specs/03_mvp_structure_specification.md`, `mvp/README.md`, `README.md`, `readme/`.

- [x] Especificar e implementar posteriormente preview y publicacion de documentos
  - Aceptacion: `/admin` distingue estado tecnico de `enabled`, permite preview segura, toggle
    sin reprocesar y conserva delete; RAG usa solo `available AND enabled`.
  - Verificar: `python -m pytest tests/test_api.py tests/test_live_knowledge.py -q` y recorrido
    manual upload/preview/disable/enable/delete.
  - Archivos: `specs/04_admin_document_lifecycle_specification.md`, `app/`, `tests/`, `README.md`.

- [x] Especificar e implementar posteriormente timeout de escucha configurable
  - Aceptacion: `PATIENT_LISTEN_TIMEOUT_MS` se valida, se muestra sin secretos, no procesa
    parciales como turnos y ofrece reintento/texto sin marcar verde al vencer.
  - Verificar: pruebas de configuracion/voz y smoke manual en Chrome/Edge.
  - Archivos: `specs/05_patient_listening_timeout_specification.md`, `.env.example`, `app/`,
    `tests/`, `readme/02_setup_local.md`.

- [x] Mantener el diagrama como fuente de arquitectura
  - Aceptacion: ASCII y subdiagramas Mermaid cubren actores, etapas, submodulos, admin, voz,
    triaje, RAG, persistencia y metricas; cada nodo tiene trazabilidad y estado.
  - Verificar: revision humana de `TRZ-*`, contraste con codigo y comandos de preflight; no
    declarar propuestas como implementadas.
  - Archivos: `specs/06_system_flow_diagram_specification.md`, `docs/arquitectura.md`,
    `mvp/`, `README.md`, `docs/informe-final.md`.

- [x] Definir y mantener pruebas unitarias e integracion
  - Aceptacion: la suite cubre contratos, SQLite/FTS5, ingestion, RAG, triaje, seguridad,
    metricas y conocimiento vivo; distingue baseline, propuestas y evidencia manual.
  - Verificar: `python -m pytest -q`, comandos enfocados, `pytest-cov` y `ruff check .` despues
    de instalar `requirements-dev.txt`; browser/proveedor real siguen evidencia manual.
  - Archivos: `specs/07_testing_unit_integration_specification.md`, `tests/`, `pyproject.toml`,
    `requirements-dev.txt`, `readme/04_metricas_y_evidencia.md`.
