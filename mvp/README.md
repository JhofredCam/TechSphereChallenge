# MVP / CRISP-DM

Este directorio ordena el MVP de seguimiento postoperatorio en las seis fases de
CRISP-DM. El contrato del producto y los comandos previstos viven en la
[especificacion del MVP](../specs/00_mvp_specification.md); este indice no la reemplaza.

## Estado del corte

Al 2026-08-08 el repositorio contiene la implementacion local bajo `app/`, la suite bajo
`tests/`, `requirements.txt`, el modulo ejecutable `app.bootstrap` y el entrypoint
`app.main`. El runtime local y las verificaciones automatizadas ya se ejecutaron; la voz
real, el cronometraje de setup y la evidencia de demo siguen siendo pendientes. Preview,
publicacion `enabled`, filtro RAG y timeout total por turno ya estan en runtime y cubiertos por
pruebas locales.

| Orden | Fase | Estado | Salida principal |
|---:|---|---|---|
| 01 | [Business Understanding](crisp-dm/01_business_understanding/README.md) | Contrato e implementacion local | Alcance, usuarios, restricciones y criterios de exito |
| 02 | [Data Understanding](crisp-dm/02_data_understanding/README.md) | Validada | Inventario, riesgos y validacion reproducible |
| 03 | [Data Preparation](crisp-dm/03_data_preparation/README.md) | Implementada y verificada localmente | Corpus procesado, chunks trazables, preview y estado documental |
| 04 | [Modeling](crisp-dm/04_modeling/README.md) | Implementada; voz manual pendiente | Respuesta grounded, triaje, timeout y voz |
| 05 | [Evaluation](crisp-dm/05_evaluation/README.md) | Pruebas automatizadas verificadas; gates manuales pendientes | Tests, compuertas, metricas y evidencia |
| 06 | [Deployment](crisp-dm/06_deployment/README.md) | Ejecutable localmente; cronometraje y demo pendientes | Setup local y demo verificable |

## Estructura aplicada

`mvp/` es el contenedor de proceso y entrega. Las seis fases ya estan bajo `mvp/crisp-dm/` y
los cuatro entregables formales tienen una ruta estable bajo `mvp/deliverables/`.

```text
mvp/
  crisp-dm/       indice y fases 01 a 06
  deliverables/   repositorio, arquitectura, informe y video
```

Indices de entrega:

- [01 Repository](deliverables/01_repository/README.md)
- [02 Architecture](deliverables/02_architecture/README.md)
- [03 Final Report](deliverables/03_final_report/README.md)
- [04 Video](deliverables/04_video/README.md)

La [spec de estructura](../specs/03_mvp_structure_specification.md) conserva `dataset/` y
`docs/` en sus rutas canonicas, y mantiene `app/`, `scripts/`, `tests/`, `specs/` y `readme/`
fuera de copias de entrega.

## Setup desde la raiz

El contrato de setup, las URLs y los comandos de preflight siguen en el
[README operativo de la raiz](../README.md#inicio-en-15-minutos). Ejecuta esos comandos desde
la raiz; este indice solo organiza el proceso y los entregables.

Las specs funcionales que deben alimentar el diagrama son:

- [`specs/04_admin_document_lifecycle_specification.md`](../specs/04_admin_document_lifecycle_specification.md).
- [`specs/05_patient_listening_timeout_specification.md`](../specs/05_patient_listening_timeout_specification.md).
- [`specs/06_system_flow_diagram_specification.md`](../specs/06_system_flow_diagram_specification.md).

## Flujo administrativo y de escucha aplicado

1. `/admin` procesa PDF/TXT/MD y muestra estado tecnico (`available`, `needs_ocr`, `processing` o
   `error`) separado de publicacion (`enabled`/`disabled`).
2. `Previsualizar` lee texto extraido por pagina; `Deshabilitar` conserva pages/chunks y excluye
   el documento de RAG; `Habilitar` lo recupera sin reingesta; `Eliminar` limpia FTS5 y conserva
   snapshots historicos sin reiniciar.
3. `/call` obtiene `PATIENT_LISTEN_TIMEOUT_MS` desde `/health`. El limite es total por turno;
   `LISTENING`, `PARTIAL`, `NO_RESPONSE`, `LISTEN_TIMEOUT`, `RECOGNITION_ERROR` y
   `RETRY_REQUIRED` no producen un turno clinico sin transcript final. El fallback textual
   permanece disponible.
4. `client_turn_id` evita duplicados, `listen_id` identifica el intento y un transcript tardio
   recibe `409 late_transcript`.

La implementacion y los contratos detallados estan en la
[spec integradora 06](../specs/06_system_flow_diagram_specification.md) y en la
[vista formal de arquitectura](deliverables/02_architecture/architecture.md).

## Evidencia automatizada del corte

Todos los resultados siguientes corresponden a la sesion del 2026-08-08:

- `python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>`:
  24 tests pasaron.
- `python -m pytest -q --basetemp <temp>`: 96 tests pasaron.
- `ruff check .`: paso sin hallazgos.
- `node --check app/web/app.js`: sintaxis valida.
- `python -m scripts.validate_dataset`: dataset valido; filas `3991/40/40/160` en los
  cuatro XLSX canonicos.
- `python -m app.bootstrap --data-dir <temp>`: proceso 104 documentos, con 103 en
  `available` y 1 en `needs_ocr`.
- El test de idempotencia de bootstrap paso: una segunda ejecucion no reprocesa contenido
  ya indexado.

El estado generado se mantiene en el directorio de datos configurado y no se copia ni se
mueve `dataset/` o `docs/`. El snapshot pre-fork permanece conservado en
`readme/01_repositorio_base_pre_fork/`.

## Orden de trabajo

1. [Fijar el alcance y los criterios](crisp-dm/01_business_understanding/README.md).
2. [Validar los XLSX y recorrer el corpus](crisp-dm/02_data_understanding/README.md) sin mover el dataset.
3. [Preparar ingestion, SQLite/FTS5 y trazabilidad](crisp-dm/03_data_preparation/README.md).
4. [Integrar el modelo, el triaje y las superficies](crisp-dm/04_modeling/README.md).
5. [Ejecutar pruebas y clasificar evidencia](crisp-dm/05_evaluation/README.md).
6. [Completar setup y demo manual](crisp-dm/06_deployment/README.md).

## Referencias canonicas

- [README operativo del reto](../README.md): problema, dataset y estado del checkout.
- [Especificacion del MVP](../specs/00_mvp_specification.md): decisiones, stack y criterios.
- [Plan de implementacion](../specs/01_implementation_plan.md): orden tecnico y checkpoints.
- [Tareas ejecutables](../specs/02_implementation_tasks.md): archivos y verificaciones previstas.
- [Estructura de entregables](../specs/03_mvp_structure_specification.md): objetivo de
  `mvp/crisp-dm/` y `mvp/deliverables/`.
- [Ciclo documental de admin](../specs/04_admin_document_lifecycle_specification.md): preview,
  habilitar, deshabilitar, filtro RAG, snapshots y eliminar.
- [Timeout de escucha](../specs/05_patient_listening_timeout_specification.md): variable,
  estados, eventos, idempotencia y comportamiento seguro.
- [Diagrama integrador](../specs/06_system_flow_diagram_specification.md): ASCII, Mermaid y
  trazabilidad del flujo completo.
- [Pruebas unitarias e integracion](../specs/07_testing_unit_integration_specification.md):
  fixtures, contratos, cobertura y frontera con evidencia manual.
- [Rubrica de evaluacion](../docs/rubrica-evaluacion.md): compuertas y metricas obligatorias.
- [Stack tecnico](../docs/stack-tecnico.md): familias de modelos permitidas.

`dataset/` y `docs/` siguen siendo canonicos. Las fases los enlazan, pero no copian su
contenido.

## Convencion de estados

- **Documentado:** el alcance o la decision esta escrito y tiene una fuente enlazada.
- **Especificado:** existe un comando o contrato previsto, pero aun no hay evidencia de
  ejecucion en este checkout.
- **Pendiente de evidencia manual:** el codigo existe, pero la comprobacion requiere
  cronometraje, navegador, microfono, audio, video o un documento externo.
- **Verificado:** solo se usa despues de conservar el comando, su salida y la fecha de
  ejecucion.
