# Sesion 2026-08-08: specs de migracion RAG de produccion

## Alcance

Se planifico el upgrade del recuperador FTS5 del MVP a una arquitectura RAG de produccion para
voz en vivo, con ChromaDB, embeddings configurables, chunking benchmarkeable, LangChain,
LangSmith, configuracion externa y rollout/rollback.

## Rama

`spec/rag-production-migration`

La rama se creo antes de editar, siguiendo `AGENTS.md`.

## Fuentes leidas

- `GUIA_AGENTE_PLANIFICADOR_Y_ESPECIFICACIONES.md`.
- `AGENTS.md`, `README.md`, `docs/rubrica-evaluacion.md` y `docs/stack-tecnico.md`.
- `specs/00_mvp_specification.md`, `specs/01_implementation_plan.md`,
  `specs/02_implementation_tasks.md` y specs 03-12 relevantes.
- Fases CRISP-DM y `docs/arquitectura.md`/`docs/informe-final.md`.
- Skills locales `spec-driven-development` y `git-commit`.

## Decisiones

1. Se generaron las Specs 13-18 como unidades independientes ordenadas por ciclo de vida.
2. La antigua `specs/12_rag_deep_dive_specification.md` se reemplazo por
   `specs/19_rag_production_migration_specification.md`, conservando `RAG-DEEP-001` como
   `Legacy ID` y actualizando su alcance a contrato integrador.
3. SQLite sigue siendo autoridad de documentos, elegibilidad, revision, fuentes, snapshots y
   citas; ChromaDB es un indice derivado.
4. FTS5 se conserva como baseline, fallback y rollback.
5. BGE-M3 y multilingual E5 son candidatos de benchmark, no una eleccion declarada antes de
   medir provider, calidad, latencia y memoria.
6. LangChain ensambla loader/retriever/contexto/prompt, pero no decide triaje, citas, seguridad,
   publicacion o delete.
7. LangSmith es opcional, redacted, fail-open y no reemplaza `events.jsonl` ni `/api/metrics`.
8. `.env.example` agrega el contrato de variables sin secretos; el runtime actual aun no consume
   las variables nuevas hasta la fase de implementacion.

## Archivos principales

- `specs/13_rag_environment_configuration_specification.md`
- `specs/14_rag_vector_store_chromadb_specification.md`
- `specs/15_rag_chunking_embedding_benchmark_specification.md`
- `specs/16_rag_langchain_orchestration_specification.md`
- `specs/17_rag_observability_langsmith_specification.md`
- `specs/18_rag_production_operations_specification.md`
- `specs/19_rag_production_migration_specification.md`
- `tasks/plan.md` y `tasks/todo.md`
- `.env.example` y documentacion sincronizada del baseline/target

## Verificacion de esta sesion

Comandos ejecutados durante la planificacion:

```text
git status --short --branch
git log --oneline -10
git switch -c spec/rag-production-migration
```

Pendientes de verificacion antes de implementar:

- validar enlaces Markdown y ausencia de referencias a la ruta eliminada de Spec 12;
- ejecutar `git diff --check`;
- ejecutar la suite baseline con `--basetemp` escribible;
- no ejecutar benchmark, Chroma, LangChain o LangSmith porque aun no existen en el runtime;
- no declarar G2, G3 real, G4 o G5 externo por documentacion.

## Estado honesto

La suite FTS5 y las superficies existentes pertenecen al baseline previo. Las capacidades nuevas
son `PROPOSED`: no hay aun resultados de recall/precision/context precision, P50/P95 de Chroma,
costos de embeddings, trazas LangSmith ni evidencia manual de rollout/rollback.
