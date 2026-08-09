# Plan de implementacion del MVP

## Orden tecnico

1. Crear configuracion tipada y mantener el baseline FTS5 sin cambios de comportamiento.
2. Extraer contratos de loader, embeddings, vector store y manifest de indice.
3. Implementar ChromaDB derivado, dual-write, hydration SQLite y reconciliacion.
4. Preparar benchmark de chunkers/providers/modelos y seleccionar candidato por gates objetivos.
5. Integrar LangChain, prompt versionado y validacion de salida sobre el agente actual.
6. Integrar LangSmith redacted, metricas por nodo, health seguro y eventos locales.
7. Implementar promotion, canary, rollback, backup y prueba de reinicio.
8. Mantener triaje, llamadas, admin, voz, README, diagrama e informe sincronizados.
9. Definir e instrumentar el logger propio con correlacion, redaccion y JSONL local sin
   reemplazar `events.jsonl` ni la autoridad de SQLite.
10. Ejecutar la bateria fail-detect unitaria e integracion y cerrar la evidencia automatizada
    antes de la evidencia manual de G2/G4/G5.

## Extensiones planificadas por dependencia

Antes de implementar cambios nuevos, se deben revisar las specs en este orden:

1. `specs/03_mvp_structure_specification.md`: ownership y rutas objetivo bajo `mvp/`.
2. `specs/04_admin_document_lifecycle_specification.md`: preview, `enabled`,
   `rag_eligible`, enable, disable y delete.
3. `specs/05_patient_listening_timeout_specification.md`: `PATIENT_LISTEN_TIMEOUT_MS` y
   estados seguros de escucha.
4. `specs/06_system_flow_diagram_specification.md`: diagrama ASCII/Mermaid, matriz de
   trazabilidad y reflejo de las tres specs anteriores.
5. `specs/07_testing_unit_integration_specification.md`: pruebas unitarias/integracion,
   fixtures, cobertura y evidencia manual asociada a los contratos.
6. `specs/13_rag_environment_configuration_specification.md`: nombres y defaults de entorno.
7. `specs/14_rag_vector_store_chromadb_specification.md`: Chroma, metadata, revision y delete.
8. `specs/15_rag_chunking_embedding_benchmark_specification.md`: matriz y decision experimental.
9. `specs/16_rag_langchain_orchestration_specification.md`: loader, prompt y runnables.
10. `specs/17_rag_observability_langsmith_specification.md`: spans, redaction y SLOs.
11. `specs/18_rag_production_operations_specification.md`: rollout, rollback y backup.
12. `specs/19_rag_production_migration_specification.md`: contrato integrador antes del codigo.
13. `specs/23_custom_logging_system.md`: logger central y eventos seguros antes de pruebas de
    trazabilidad.
14. `specs/24_testing_suite.md`: validacion fail-detect despues de estabilizar el contrato de
    logging e instrumentacion.

La cuarta spec es un checkpoint de arquitectura: no se debe comenzar la implementacion de una
extension si el diagrama no muestra su bloque, transiciones, estado y verificacion. La quinta
spec debe revisarse antes de implementar cada contrato para evitar pruebas desconectadas del flujo.

## Componentes y dependencias

| Componente | Depende de | Riesgo | Mitigacion |
|---|---|---|---|
| Configuracion | Ninguno | Rutas distintas por SO | `pathlib`, `.env.example`, valores locales |
| SQLite/FTS5 | Python | Build sin FTS5 | Mantener baseline y rollback probado |
| ChromaDB | configuracion y volumen | version/dimension incompatibles | manifest, preflight y reconciliacion |
| Embeddings | modelo precargado | cold start, RAM, dimension | benchmark, cache y no-download |
| Ingestion | PyMuPDF | PDF sin capa de texto | Estado `needs_ocr`, no fingir disponibilidad |
| Dataset | openpyxl | XLSX sin dimensiones declaradas | Iterar filas y validar encabezados |
| LLM | httpx, API key | Cuota/modelo retirado | Modelo en entorno, fallback extractivo auditable |
| Voz | Chrome/Edge | API Web Speech variable | texto, MediaRecorder/STT como fallback |
| Frontend | API | permiso de microfono | instrucciones visibles y estado de error |
| Admin documental | documentos procesados | toggle y preview pueden divergir del RAG | bandera `enabled`, filtro activo y pruebas de revision |
| Escucha paciente | navegador | no existe timer propio en el baseline | variable de entorno, estados y fallback textual |
| LangChain | contratos RAG | cadena opaca u overhead | runnables visibles, timeouts y DTO estable |
| LangSmith | callback opcional | fuga PII o dependencia de red | redaction, sample rate y fail-open |
| Logger propio | instrumentacion transversal | ruido, PII o sink bloqueante | schema, redaction, JSONL separado y fail-open |
| Suite fail-detect | servicios y contratos | mocks que ocultan regresiones | oraculos de estado, persistencia y eventos |
| Rollout | indice versionado | regresion o rollback tardio | shadow, canary, puntero y FTS5 |

## Paralelismo

- Configuracion, qrels/benchmark, redaction de observabilidad y loaders pueden avanzar en
  paralelo despues de fijar interfaces.
- El contrato del logger propio puede avanzar aislado de la suite; su instrumentacion se
  integra despues de estabilizar los nombres de eventos y antes de cerrar los tests.
- Chroma y base de datos deben coordinar IDs, revision, estado de indice y orden de delete.
- LangChain/prompt y operaciones pueden avanzar en paralelo despues de estabilizar `SearchResult`.
- La suite fail-detect se ejecuta secuencialmente despues del logger y puede distribuir sus
  fixtures por area sin editar simultaneamente el mismo contrato.
- README, diagrama, informe y bitacora se cierran despues de pruebas, rollback y comandos reales.

## Checkpoints

1. `pytest` pasa para base, FTS5, configuracion, chunking y triaje sin credenciales.
2. Bootstrap procesa un fixture y marca un PDF sin texto como `needs_ocr` sin descargar modelos.
3. Chroma backfill es idempotente y el manifest valida dimension/metrica/version.
4. Upload/disable/enable/delete pasa con SQLite authority y Chroma sin reinicio.
5. Benchmark reporta calidad, latencia y memoria contra FTS5; el candidato queda justificado.
6. LangChain conserva grounding, abstencion, cita, triage y fallback.
7. LangSmith redacted no bloquea cuando esta caido o desactivado.
8. `/call` conserva texto y voz manual pendiente/validada segun evidencia real.
9. `python -m pytest -q`, preflight y rollback quedan documentados en README.
10. La migracion documental no inicia hasta que los enlaces y el ownership de `mvp/` esten
   verificados.
11. El admin y el timeout se prueban de forma independiente antes de actualizar el diagrama
   publicado.
12. Las pruebas unitarias y de integracion deben aislar proveedores, datos y estado generado antes
   de servir como evidencia de los gates.
13. El logger propio debe demostrar stack traces redacted, correlacion de llamada/turno/VAD/RAG
   y fail-open antes de habilitar la suite de integracion.
14. La suite fail-detect debe dejar P0/P1 en rojo ante regresiones de triaje, citas, delete,
   timeout, render seguro o fuga de secretos.
