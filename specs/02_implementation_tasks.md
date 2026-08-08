# Tareas ejecutables del MVP

Esta lista conserva el backlog original del MVP. Sus casillas no sustituyen el estado de
implementacion ni la evidencia descritos en `mvp/`, `README.md` y `docs/informe-final.md`; una
tarea puede permanecer sin marcar aunque exista una implementacion local verificada. Las nuevas
tareas de abajo pertenecen al siguiente corte y tampoco se ejecutaron en esta sesion.

- [ ] Crear configuracion y esquema SQLite
  - Aceptacion: `init_database()` crea tablas, FTS5 y directorios locales sin secretos.
  - Verificar: `python -m pytest tests/test_database.py -q`.
  - Archivos: `app/config.py`, `app/database.py`, `app/schemas.py`.

- [ ] Implementar ingestion y ciclo de vida documental
  - Aceptacion: PDF/TXT/MD se procesan por pagina, se generan chunks y se registra
    `available`, `needs_ocr` o `error`.
  - Verificar: `python -m pytest tests/test_ingestion.py -q`.
  - Archivos: `app/services/ingestion.py`, `app/services/documents.py`.

- [ ] Implementar recuperacion y trazabilidad
  - Aceptacion: cada resultado contiene documento, pagina, chunk, cita y revision del corpus;
    borrar elimina los resultados futuros.
  - Verificar: `python -m pytest tests/test_live_knowledge.py -q`.
  - Archivos: `app/services/rag.py`, `app/database.py`.

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

## Tareas del siguiente corte

- [ ] Reorganizar el paquete de entregables bajo `mvp/`
  - Aceptacion: las seis fases quedan previstas bajo `mvp/crisp-dm/`, los cuatro entregables
    bajo `mvp/deliverables/` y no se copian `dataset/` ni `docs/`.
  - Verificar: revisar ownership, enlaces relativos y ausencia de rutas prohibidas; no ejecutar
    una migracion en esta sesion de planificacion.
  - Archivos: `specs/03_mvp_structure_specification.md`, `mvp/README.md`, `README.md`, `readme/`.

- [ ] Especificar e implementar posteriormente preview y publicacion de documentos
  - Aceptacion: `/admin` distingue estado tecnico de `enabled`, permite preview segura, toggle
    sin reprocesar y conserva delete; RAG usa solo `available AND enabled`.
  - Verificar: `python -m pytest tests/test_api.py tests/test_live_knowledge.py -q` y recorrido
    manual upload/preview/disable/enable/delete.
  - Archivos: `specs/04_admin_document_lifecycle_specification.md`, `app/`, `tests/`, `README.md`.

- [ ] Especificar e implementar posteriormente timeout de escucha configurable
  - Aceptacion: `PATIENT_LISTEN_TIMEOUT_MS` se valida, se muestra sin secretos, no procesa
    parciales como turnos y ofrece reintento/texto sin marcar verde al vencer.
  - Verificar: pruebas de configuracion/voz y smoke manual en Chrome/Edge.
  - Archivos: `specs/05_patient_listening_timeout_specification.md`, `.env.example`, `app/`,
    `tests/`, `readme/02_setup_local.md`.

- [ ] Mantener el diagrama como fuente de arquitectura
  - Aceptacion: ASCII y subdiagramas Mermaid cubren actores, etapas, submodulos, admin, voz,
    triaje, RAG, persistencia y metricas; cada nodo tiene trazabilidad y estado.
  - Verificar: revision humana de `TRZ-*`, contraste con codigo y comandos de preflight; no
    declarar propuestas como implementadas.
  - Archivos: `specs/06_system_flow_diagram_specification.md`, `docs/arquitectura.md`,
    `mvp/`, `README.md`, `docs/informe-final.md`.
