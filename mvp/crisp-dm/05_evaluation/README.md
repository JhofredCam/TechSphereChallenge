# 05 - Evaluation

## Objetivo

Medir el comportamiento observable del MVP y decidir si pasa las compuertas eliminatorias y
los criterios de calidad. La evaluacion debe conservar comandos, salidas y contexto de
ejecucion; nunca sustituir evidencia por una intencion de diseno.

## Entradas

- Aplicacion, pruebas y logs producidos por las fases 03, 04 y 06.
- [Rubrica de evaluacion](../../../docs/rubrica-evaluacion.md), especialmente G1-G5 y metricas.
- [Tareas ejecutables](../../../specs/02_implementation_tasks.md).
- [Guia de metricas y evidencia](../../../readme/04_metricas_y_evidencia.md).
- [Spec de admin](../../../specs/04_admin_document_lifecycle_specification.md), para preview y
  enable/disable sin confundirlos con delete.
- [Spec de timeout](../../../specs/05_patient_listening_timeout_specification.md), para separar
  escucha, silencio y latencia de respuesta.
- [Spec de diagrama](../../../specs/06_system_flow_diagram_specification.md), como matriz de
  trazabilidad del cambio.
- [Spec de pruebas](../../../specs/07_testing_unit_integration_specification.md), para separar
  pruebas automatizadas, cobertura y evidencia manual.

## Salidas

- Resultados de pruebas unitarias, integracion, dataset y smoke manual.
- Evidencia de G1: repositorio, diagrama, informe y video.
- Evidencia de G2: setup limpio cronometrado en <=15 minutos.
- Evidencia de G3: modelo exacto, familia permitida, configuracion y proveedor coherentes.
- Evidencia de G4: saludo y pregunta trivial con voz de ida y vuelta.
- Evidencia de G5: upload, respuesta grounded, delete y olvido sin reinicio.
- Evidencia local de admin: preview, disable, abstencion, enable, recuperacion, delete y
  snapshots; la demostracion G5 externa sigue pendiente.
- Evidencia local de timeout: configuracion, estados, eventos, carrera, `client_turn_id`,
  `listen_id` y `late_transcript`; el smoke de Chrome/Edge sigue pendiente.
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
- [x] La preview, el toggle documental y el timeout configurable tienen runtime y pruebas
  automatizadas locales; la evidencia manual de UI/voz y G5 externo sigue pendiente.

## Verificacion y evidencia

Comandos de verificacion desde la raiz:

```text
python -m pytest -q --basetemp <temp>
python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>
ruff check .
node --check app/web/app.js
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>
```

Resultado del 2026-08-08:

- `python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>`:
  24 tests pasaron.
- `python -m pytest -q --basetemp <temp>`: 96 tests pasaron.
- `ruff check .`: paso sin hallazgos.
- `node --check app/web/app.js`: sintaxis valida.
- `python -m scripts.validate_dataset`: dataset valido con filas `3991/40/40/160`.
- `python -m app.bootstrap --data-dir <temp>`: 104 documentos procesados; 103
  `available` y 1 `needs_ocr`.
- La prueba de idempotencia del bootstrap paso en la suite.

La matriz de [metricas y evidencia](../../../readme/04_metricas_y_evidencia.md) y los campos
`PENDIENTE` de [informe-final.md](../../../docs/informe-final.md) distinguen la evidencia local
de las comprobaciones que faltan.

## Dependencias

- Depende de datos preparados, modelo integrado, logs y superficies web reales.
- Depende de una version de navegador compatible para G4.
- Depende de credenciales solo para el camino remoto; los tests locales deben conservar un
  modo auditable sin secreto.

## Estado

**Evaluacion automatizada verificada; preview/toggle/timeout estan probados localmente. G2, G4,
Groq/Whisper real y G5 externo aun no estan aprobados; G1 conserva el pendiente del video
(2026-08-08).**

## Actualizacion de la estrategia de pruebas

La implementacion de `specs/07_testing_unit_integration_specification.md` agrego 31 casos
ejecutables a la suite concurrente y dejo 93 casos verificados en total. Los nuevos modulos son
`test_config_contracts.py`, `test_dataset_contracts.py`, `test_http_contracts.py`,
`test_schema_contracts.py`, `test_structure.py` y `test_voice.py`; tambien se ampliaron
`test_agent.py`, `test_bootstrap.py`, `test_calls.py`, `test_ingestion.py` y
`test_metrics.py`.

Evidencia local del 2026-08-08, desde la raiz, en Windows/Python 3.13.3:

- Suite completa: `96 passed` con un `--basetemp` escribible.
- API y conocimiento vivo: `8 passed`.
- Agente, triaje, llamadas y metricas: `28 passed`.
- Base, ingestion y bootstrap: `16 passed`.
- Cobertura de `app` y `scripts` con ramas: `80.07%`, `96 passed`; el XML se escribio en un
  temporal y no se agrego al repositorio.
- `ruff check .`: sin hallazgos.
- `python -m scripts.validate_dataset`: valido; `3991/40/40/160` filas.
- `python -m app.bootstrap --data-dir <temp>/techsphere-bootstrap`: 104 documentos, 103
  `available` y 1 `needs_ocr`.
- Comprobacion estructural de `mvp/`: 13 rutas requeridas y ninguna copia prohibida.
- `git diff --check`: sin errores.

La eliminacion fisica local, el snapshot, preview/toggle, timeout, idempotencia, eventos y
payloads sin `stored_path` tienen cobertura automatizada. La validacion MIME independiente no
existe en el runtime y queda como brecha documentada. Browser, microfono, TTS, Groq/Whisper real,
G2 y G5 externo permanecen `MANUAL_PENDING`; no se infieren desde mocks ni desde la cobertura.
