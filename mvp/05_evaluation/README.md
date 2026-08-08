# 05 - Evaluation

## Objetivo

Medir el comportamiento observable del MVP y decidir si pasa las compuertas eliminatorias y
los criterios de calidad. La evaluacion debe conservar comandos, salidas y contexto de
ejecucion; nunca sustituir evidencia por una intencion de diseno.

## Entradas

- Aplicacion, pruebas y logs producidos por las fases 03, 04 y 06.
- [Rubrica de evaluacion](../../docs/rubrica-evaluacion.md), especialmente G1-G5 y metricas.
- [Tareas ejecutables](../../specs/02_implementation_tasks.md).
- [Guia de metricas y evidencia](../../readme/04_metricas_y_evidencia.md).

## Salidas

- Resultados de pruebas unitarias, integracion, dataset y smoke manual.
- Evidencia de G1: repositorio, diagrama, informe y video.
- Evidencia de G2: setup limpio cronometrado en <=15 minutos.
- Evidencia de G3: modelo exacto, familia permitida, configuracion y proveedor coherentes.
- Evidencia de G4: saludo y pregunta trivial con voz de ida y vuelta.
- Evidencia de G5: upload, respuesta grounded, delete y olvido sin reinicio.
- P50/P95 de latencia, tokens por turno/llamada, invocaciones, consultas RAG y costo
  estimado, todos vinculados a logs.
- Matriz de triaje y resumen de limitaciones, falsos positivos y falsos negativos.

## Tareas concretas

1. Ejecutar primero pruebas de base, ingestion, dataset, RAG, triaje, agente, API y llamadas.
2. Repetir la prueba de aprender/olvidar con un documento que no pertenezca al corpus
   entregado.
3. Cronometrar setup desde entorno limpio siguiendo solo la documentacion operativa.
4. Verificar el modelo configurado contra la lista cerrada de familias permitidas.
5. Ejecutar smoke manual de microfono, transcripcion, audio, abstencion y triaje.
6. Calcular las metricas con timestamps del sistema, no con estimaciones visuales.
7. Conservar salidas, capturas y logs con fecha, commit, entorno y configuracion no secreta.
8. Registrar cualquier prueba no ejecutada y su razon en el informe final.

## Criterios de aceptacion

- [x] Los comandos automatizados ejecutados terminan con el resultado esperado y tienen
  salida fechada y reproducible.
- [ ] Las cinco compuertas tienen evidencia observable; si alguna falla, se marca sin
  eufemismos y no se declara el MVP listo.
- [x] La implementacion calcula P50/P95 desde timestamps de fin de habla e inicio de audio;
  falta una muestra de voz real para reportar valores de demo.
- [ ] Tokens, invocaciones, consultas RAG y costo concuerdan con los logs.
- [x] Las pruebas automatizadas cubren escenarios rojo, amarillo, verde y ambiguo sin
  degradar una decision previa.
- [x] G4 y G5 no se declaran aprobadas con mocks; se separan los tests locales de la
  evidencia manual requerida.

## Verificacion y evidencia

Comandos de verificacion desde la raiz:

```text
python -m pytest -q --basetemp <temp>
ruff check .
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>
```

Resultado del 2026-08-08:

- `python -m pytest -q --basetemp <temp>`: 38 tests pasaron.
- `ruff check .`: paso sin hallazgos.
- `python -m scripts.validate_dataset`: dataset valido con filas `3991/40/40/160`.
- `python -m app.bootstrap --data-dir <temp>`: 104 documentos procesados; 103
  `available` y 1 `needs_ocr`.
- La prueba de idempotencia del bootstrap paso en la suite.

La matriz de [metricas y evidencia](../../readme/04_metricas_y_evidencia.md) y los campos
`PENDIENTE` de [informe-final.md](../../docs/informe-final.md) distinguen la evidencia local
de las comprobaciones que faltan.

## Dependencias

- Depende de datos preparados, modelo integrado, logs y superficies web reales.
- Depende de una version de navegador compatible para G4.
- Depende de credenciales solo para el camino remoto; los tests locales deben conservar un
  modo auditable sin secreto.

## Estado

**Evaluacion automatizada verificada; G2, G4 y G5 aun no estan aprobadas y G1 conserva el
pendiente del video (2026-08-08).**
