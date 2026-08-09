# Metricas y evidencia

## Estado

La instrumentacion y la agregacion local estan implementadas; los valores de una llamada de
voz real siguen `PENDIENTES` al 2026-08-08. La [rubrica](../docs/rubrica-evaluacion.md#5-qué-debe-reportar-tu-readme)
exige reportar estos numeros y contrastarlos con los logs.

La estrategia de pruebas esta definida en
[specs/07_testing_unit_integration_specification.md](../specs/07_testing_unit_integration_specification.md).
Las cifras historicas de la documentacion pertenecen a la sesion de implementacion previa; en
esta sincronizacion se ejecutaron pytest, Ruff, validacion del dataset y bootstrap, con los
resultados fechados de abajo.

La [spec del diagrama](../specs/06_system_flow_diagram_specification.md) define la trazabilidad
entre eventos, submodulos y evidencia. La [spec de timeout](../specs/05_patient_listening_timeout_specification.md)
separa el tiempo de escucha del paciente de la latencia oficial de respuesta; el valor de
`.env.example` se valida y llega al navegador por `/health`.
La migracion RAG añade configuracion, Chroma, benchmark y LangSmith en las Specs 13-19, pero sus
valores siguen `PENDIENTES` hasta ejecutar el runtime y conservar artefactos fechados.

## Metricas obligatorias

| Metrica | Definicion | Fuente esperada | Resultado |
|---|---|---|---|
| Latencia P50/P95 | Percentiles de `audio_started_at - speech_ended_at` por turno | Log JSONL y `/api/metrics` | Implementado y cubierto por tests; muestra de voz real PENDIENTE |
| Tokens de entrada | Tokens enviados al modelo por turno y llamada | Log del adaptador LLM | Contrato y tests verificados; demo real PENDIENTE |
| Tokens de salida | Tokens generados por turno y llamada | Log del adaptador LLM | Contrato y tests verificados; demo real PENDIENTE |
| Invocaciones al modelo | Conteo por turno | Log de llamada | Implementado; demo real PENDIENTE |
| Consultas RAG | Conteo por llamada y resultados con fuente | Log de recuperacion | Implementado; demo real PENDIENTE |
| Costo estimado | Precio documentado por millon de tokens aplicado a cada llamada | Informe + logs | PENDIENTE; falta precio vigente y muestra de proveedor |
| Ciclo admin | Preview textual, disable/enable, filtro RAG, delete y snapshot | `tests/test_admin_lifecycle.py`, API y UI | Tests locales ejecutados; smoke manual/G5 externo PENDIENTE |
| Timeout de escucha | Duracion y resultado de `PATIENT_LISTEN_TIMEOUT_MS` | `tests/test_timeout.py`, `voice-events`, navegador | 24 tests enfocados; smoke manual Chrome/Edge PENDIENTE |
| Recall/precision/hit rate | qrels por consulta y top-k | runner de benchmark | PENDIENTE; FTS5 baseline debe ejecutarse primero |
| Context precision | relevancia de chunks enviados al prompt | qrels + trace redacted | PENDIENTE |
| MRR/nDCG | orden y relevancia graduada | runner de benchmark | PENDIENTE |
| Retrieval latency | embedding, Chroma/FTS5, fusion, hydration y total | JSONL/LangSmith redacted | PENDIENTE |
| Index lag | disponible SQLite versus vector listo | index manager/health | PENDIENTE |
| Citation validity | cita coincide con fuente elegible y revision | tests + eventos | PENDIENTE; objetivo 99.5% |
| Leakage | documento disabled/deleted recuperable | lifecycle/reconcile tests | objetivo 0 |
| LangSmith privacy | spans sin PII, secrets, audio o chunks | redaction tests + traza staging | PENDIENTE |

Usar los nombres de campo del contrato previsto: `call_id`, `turn_id`, `speech_ended_at`,
`audio_started_at`, `latency_ms`, `input_tokens`, `output_tokens`, `model_calls`,
`rag_queries`, `source_ids` y `model_version`. Si un proveedor no devuelve tokens, registrar
el metodo de conteo y no presentar una cifra como exacta.

## Formula de costo

Completar con precios vigentes y fecha de consulta:

```text
costo_llamada = (tokens_entrada / 1_000_000 * precio_entrada) +
                 (tokens_salida / 1_000_000 * precio_salida)
```

El informe debe declarar moneda, precios, proveedor, modelo, fecha y si STT/TTS se incluyen
o se excluyen. No llenar `PENDIENTE` con una estimacion sin logs.

## Compuertas

| Gate | Evidencia necesaria | Estado 2026-08-08 |
|---|---|---|
| G1 | Repositorio, diagrama, informe y video completos | PENDIENTE; falta video de entrega |
| G2 | Setup limpio cronometrado en <=15 minutos siguiendo solo el README | `MANUAL_PENDING`: falta cronometraje desde entorno limpio |
| G3 | Modelo exacto, familia Meta Llama permitida, configuracion y uso coherentes | `TESTED` local; `MANUAL_PENDING` para uso remoto real |
| G4 | Saludo y pregunta trivial con voz de ida y vuelta | `MANUAL_PENDING`: falta smoke manual con microfono y audio |
| G5 | Upload, preview, disable/enable, uso, delete y olvido de documento nuevo sin reinicio | `TESTED` local; `MANUAL_PENDING` para demo con documento externo |

## Pruebas de calidad

Conservar resultados de:

- Validacion de hojas `result`, JSON embebido y joins del dataset.
- Recuperacion con fuente antes y despues de borrar.
- Preview, estado `enabled` y revision de documentos en `/admin`.
- Exclusión de documentos deshabilitados de nuevas consultas RAG y recuperacion al habilitar.
- Abstencion cuando no hay evidencia.
- Triaje rojo sin degradacion, amarillo con alerta y ambiguo con aclaracion.
- Resumen de cierre y persistencia de alerta.
- Voz en navegador, fallback textual y comportamiento ante permisos denegados.
- Recuperacion Chroma/FTS5, restart, stale vectors, reconciliacion y rollback.
- Comparacion reproducible de al menos tres chunkers y varias combinaciones de provider/modelo.
- Redaction y retencion de trazas LangSmith, sin usar su disponibilidad como gate clinico.
- Timeout de escucha, resultado parcial, no respuesta y reintento, sin inferir una decision
  clinica desde el silencio; tests locales pasaron y smoke manual sigue PENDIENTE.

## Formato de evidencia

Cada registro debe incluir:

```text
fecha_utc, commit, entorno, comando_o_url, resultado, artefacto, observaciones
```

Los artefactos pueden ser salidas de comandos, logs JSONL, capturas o video. Enlazarlos
desde el informe final y conservar los secretos fuera de los artefactos. Si una prueba no se
ejecuta, escribir `PENDIENTE` con la razon y no inferir el resultado.

## Evidencia del 2026-08-08

| Comando o prueba | Resultado |
|---|---|
| `python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>` | 24 tests pasaron |
| `python -m pytest -q --basetemp <temp>` | 96 tests pasaron |
| `ruff check .` | Paso sin hallazgos |
| `node --check app/web/app.js` | Sintaxis valida |
| `python -m scripts.validate_dataset` | Dataset valido: `3991/40/40/160` |
| `python -m app.bootstrap --data-dir <temp>` | 104 documentos procesados: `available=103`, `needs_ocr=1` |
| Idempotencia de bootstrap | Segunda ejecucion sin reprocesar contenido ya indexado |

Estas cifras no son metricas de una conversacion de voz. No se llenan P50/P95, costo ni
tokens de demo sin logs producidos por una sesion real.

## Comandos de verificacion

```text
python -m pytest -q --basetemp <temp>
ruff check .
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>
```

Los comandos se deben ejecutar desde la raiz con el servidor real para G4/G5; mocks solo
pueden cubrir pruebas unitarias y de contrato.

## Actualizacion de pruebas 2026-08-08

La estrategia de `specs/07_testing_unit_integration_specification.md` ya es ejecutable en este
checkout. Se agregaron 31 casos nuevos y las regresiones de concurrencia dejaron la suite en
`96 passed`. La cobertura se ejecuto con `--cov=app --cov=scripts --cov-branch --cov-fail-under=80`
y alcanzo `80.07%`; el XML se
escribio en un temporal fuera del repositorio. No se declara cobertura de `app/web/app.js` con
pytest-cov.

Resultados enfocados:

- `tests/test_api.py tests/test_live_knowledge.py`: `8 passed`.
- `tests/test_agent.py tests/test_triage.py tests/test_calls.py tests/test_metrics.py`:
  `28 passed`.
- `tests/test_database.py tests/test_ingestion.py tests/test_bootstrap.py`: `16 passed`.
- `ruff check .`: sin hallazgos.
- `python -m scripts.validate_dataset`: valido, filas `3991/40/40/160`.
- `python -m app.bootstrap --data-dir <temp>/techsphere-bootstrap`: `104` documentos,
  `103 available` y `1 needs_ocr`.
- Estructura de `mvp/`: 13 rutas requeridas, sin copias prohibidas.
- `git diff --check`: sin errores.

La eliminacion fisica local, snapshot, preview/toggle, filtro RAG, timeout, idempotencia, eventos,
metricas y ausencia de `stored_path`/secretos tienen evidencia automatizada. La API no valida MIME
de forma independiente; esta brecha permanece documentada. La cobertura no cambia el estado
`MANUAL_PENDING` de navegador, microfono, TTS, Groq/Whisper real, G2 ni G5 externo. La sesion se
registro como `working tree/no commit`, sin inventar fecha de commit ni metricas de voz reales.
