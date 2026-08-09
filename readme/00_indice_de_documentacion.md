# Indice de documentacion

Este directorio contiene la documentacion operativa del MVP y una copia historica del
README del repositorio base anterior al fork. Las fuentes originales del reto siguen en sus
rutas canonicas. El contexto oficial se conserva ademas como snapshot reducido en
`ParticipantArtifacts/`, sin `dataset/`, para que las guias de agentes tengan una referencia
local y versionada.

## Navegacion

| Documento | Uso |
|---|---|
| [Repositorio base pre-fork](01_repositorio_base_pre_fork/README.md) | Snapshot del README original con enlaces relativos corregidos |
| [Manifest del snapshot](01_repositorio_base_pre_fork/MANIFEST.md) | Origen commit `595989d` y reglas de preservacion |
| [Setup local](02_setup_local.md) | Instalacion, bootstrap y arranque operativos |
| [Demo funcional](03_demo_funcional.md) | Guion de consola, conocimiento vivo y llamada de voz |
| [Metricas y evidencia](04_metricas_y_evidencia.md) | Metricas obligatorias, compuertas y artefactos verificables |
| [Bitacora de sesiones](06_bitacora_de_sesiones/README.md) | Memoria de decisiones y estado del checkout |

## Documentacion de producto

- [Indice CRISP-DM del MVP](../mvp/README.md).
- [Arquitectura](../docs/arquitectura.md).
- [Informe final, estado del MVP](../docs/informe-final.md).
- [README actual del repositorio](../README.md).
- [Especificacion del MVP](../specs/00_mvp_specification.md).
- [Plan de implementacion](../specs/01_implementation_plan.md).
- [Tareas ejecutables](../specs/02_implementation_tasks.md).
- [Spec de estructura bajo `mvp/`](../specs/03_mvp_structure_specification.md).
- [Spec de ciclo documental de `/admin`](../specs/04_admin_document_lifecycle_specification.md).
- [Spec de timeout de escucha](../specs/05_patient_listening_timeout_specification.md).
- [Spec de diagrama normativo](../specs/06_system_flow_diagram_specification.md).
- [Spec de pruebas unitarias e integracion](../specs/07_testing_unit_integration_specification.md).
- [Spec de inventario admin responsive, con estados humanos y sin identidad tecnica visible](../specs/08_admin_inventory_ux_specification.md).
- [Spec de previsualizacion del archivo original](../specs/09_admin_source_preview_specification.md).
- [Spec de explorador HTML de arquitectura](../specs/10_architecture_explorer_specification.md).
- [Spec de UX Writing y mensajes del bot](../specs/11_conversational_ux_writing_specification.md).
- [Spec de configuracion RAG](../specs/13_rag_environment_configuration_specification.md).
- [Spec de ChromaDB y vector store](../specs/14_rag_vector_store_chromadb_specification.md).
- [Spec de benchmark de chunking y embeddings](../specs/15_rag_chunking_embedding_benchmark_specification.md).
- [Spec de orquestacion LangChain](../specs/16_rag_langchain_orchestration_specification.md).
- [Spec de observabilidad LangSmith](../specs/17_rag_observability_langsmith_specification.md).
- [Spec de operacion RAG](../specs/18_rag_production_operations_specification.md).
- [Spec integradora de migracion RAG](../specs/19_rag_production_migration_specification.md).

## Estado de evidencia

Al 2026-08-08 el checkout tiene implementacion en `app/`, pruebas en `tests/`,
`requirements.txt`, `requirements-dev.txt`, `app.bootstrap` y `app.main`. Pasaron 96 tests con
`python -m pytest -q --basetemp <temp>`, `ruff check .` no reporto hallazgos y el validador
confirmo el dataset `3991/40/40/160`. El bootstrap proceso 104 documentos: 103
`available` y 1 `needs_ocr`; su prueba de idempotencia tambien paso.

El setup esta documentado pero G2 sigue `PENDIENTE` de cronometraje desde un entorno limpio.
G4 sigue `PENDIENTE` de smoke manual con microfono y audio. G5 tiene prueba automatizada e
integracion local verificadas, pero sigue `PENDIENTE` de evidencia en demo con un documento
externo al corpus. G1 conserva el pendiente del video de entrega.

El snapshot pre-fork de `readme/01_repositorio_base_pre_fork/` se conserva sin incorporar
cambios posteriores. El snapshot oficial bajo `ParticipantArtifacts/` es la excepcion documental
intencional y no incluye `dataset/`; el dataset de trabajo sigue en la raiz.

La reestructuracion de entregables, la ampliacion de `/admin`, el timeout de escucha y el
diagrama integrado estan aplicados y sincronizados. El contrato estatico del inventario admin
esta documentado. El upgrade Chroma/embeddings/LangChain/LangSmith queda especificado en 13-19,
pero su runtime y benchmark permanecen pendientes; la evidencia manual de navegador, G2 y G5
externo tambien permanece pendiente.

## Fuentes canonicas

- El contrato oficial del reto, la rubrica y el stack permitido estan en
  [`ParticipantArtifacts/`](ParticipantArtifacts/README.md), snapshot de
  `TechSphere2026/ParticipantArtifacts` en `main` (`595989d`).
- El dataset permanece en [`dataset/`](../dataset/).
- La rubrica y el stack permanecen en [`docs/`](../docs/).
- El README base actual permanece en [`README.md`](../README.md).
