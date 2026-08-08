# MVP / CRISP-DM

Este directorio ordena el MVP de seguimiento postoperatorio en las seis fases de
CRISP-DM. El contrato del producto y los comandos previstos viven en la
[especificacion del MVP](../specs/00_mvp_specification.md); este indice no la reemplaza.

## Estado del corte

Al 2026-08-08 el repositorio contiene la implementacion local bajo `app/`, la suite bajo
`tests/`, `requirements.txt`, el modulo ejecutable `app.bootstrap` y el entrypoint
`app.main`. El runtime local y las verificaciones automatizadas ya se ejecutaron; la voz
real, el cronometraje de setup y la evidencia de demo siguen siendo pendientes.

| Orden | Fase | Estado | Salida principal |
|---:|---|---|---|
| 01 | [Business Understanding](01_business_understanding/README.md) | Contrato e implementacion local | Alcance, usuarios, restricciones y criterios de exito |
| 02 | [Data Understanding](02_data_understanding/README.md) | Validada | Inventario, riesgos y validacion reproducible |
| 03 | [Data Preparation](03_data_preparation/README.md) | Implementada y verificada localmente | Corpus procesado, chunks trazables y estado documental |
| 04 | [Modeling](04_modeling/README.md) | Implementada; voz manual pendiente | Respuesta grounded, triaje y voz |
| 05 | [Evaluation](05_evaluation/README.md) | Pruebas automatizadas verificadas; gates manuales pendientes | Tests, compuertas, metricas y evidencia |
| 06 | [Deployment](06_deployment/README.md) | Ejecutable localmente; cronometraje y demo pendientes | Setup local y demo verificable |

## Evidencia automatizada del corte

Todos los resultados siguientes corresponden a la sesion del 2026-08-08:

- `python -m pytest -q --basetemp <temp>`: 38 tests pasaron.
- `ruff check .`: paso sin hallazgos.
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

1. Fijar el alcance y los criterios de la fase 01.
2. Validar los XLSX y recorrer el corpus de la fase 02 sin mover el dataset.
3. Implementar ingestion, SQLite/FTS5 y trazabilidad en la fase 03.
4. Integrar el modelo permitido, el triaje conservador y las superficies de la fase 04.
5. Ejecutar pruebas automatizadas y clasificar la evidencia de G1-G5 en la fase 05.
6. Completar el cronometraje de 15 minutos y el recorrido manual de demo en la fase 06.

## Referencias canonicas

- [README del reto](../README.md): problema, dataset y entregables originales.
- [Especificacion del MVP](../specs/00_mvp_specification.md): decisiones, stack y criterios.
- [Plan de implementacion](../specs/01_implementation_plan.md): orden tecnico y checkpoints.
- [Tareas ejecutables](../specs/02_implementation_tasks.md): archivos y verificaciones previstas.
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
