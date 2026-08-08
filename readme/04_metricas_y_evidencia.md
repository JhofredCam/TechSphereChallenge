# Metricas y evidencia

## Estado

La instrumentacion y la agregacion local estan implementadas; los valores de una llamada de
voz real siguen `PENDIENTES` al 2026-08-08. La [rubrica](../docs/rubrica-evaluacion.md#5-qué-debe-reportar-tu-readme)
exige reportar estos numeros y contrastarlos con los logs.

La [spec del diagrama](../specs/06_system_flow_diagram_specification.md) define la trazabilidad
entre eventos, submodulos y evidencia. La [spec de timeout](../specs/05_patient_listening_timeout_specification.md)
separa el tiempo de escucha del paciente de la latencia oficial de respuesta; el valor de
`.env.example` aun no tiene efecto en el runtime.

## Metricas obligatorias

| Metrica | Definicion | Fuente esperada | Resultado |
|---|---|---|---|
| Latencia P50/P95 | Percentiles de `audio_started_at - speech_ended_at` por turno | Log JSONL y `/api/metrics` | Implementado y cubierto por tests; muestra de voz real PENDIENTE |
| Tokens de entrada | Tokens enviados al modelo por turno y llamada | Log del adaptador LLM | Contrato y tests verificados; demo real PENDIENTE |
| Tokens de salida | Tokens generados por turno y llamada | Log del adaptador LLM | Contrato y tests verificados; demo real PENDIENTE |
| Invocaciones al modelo | Conteo por turno | Log de llamada | Implementado; demo real PENDIENTE |
| Consultas RAG | Conteo por llamada y resultados con fuente | Log de recuperacion | Implementado; demo real PENDIENTE |
| Costo estimado | Precio documentado por millon de tokens aplicado a cada llamada | Informe + logs | PENDIENTE; falta precio vigente y muestra de proveedor |
| Timeout de escucha | Duracion y resultado de `PATIENT_LISTEN_TIMEOUT_MS` | Eventos de voz y navegador | Especificado; no aplicado en este baseline |

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
| G2 | Setup limpio cronometrado en <=15 minutos siguiendo solo el README | PENDIENTE de cronometraje desde entorno limpio |
| G3 | Modelo exacto, familia Meta Llama permitida, configuracion y uso coherentes | Verificado en configuracion, codigo y tests; uso remoto en vivo no ejercitado |
| G4 | Saludo y pregunta trivial con voz de ida y vuelta | PENDIENTE de smoke manual con microfono y audio |
| G5 | Upload, uso, delete y olvido de documento nuevo sin reinicio | Prueba automatizada e integracion local verificadas; PENDIENTE de demo con documento externo |

## Pruebas de calidad

Conservar resultados de:

- Validacion de hojas `result`, JSON embebido y joins del dataset.
- Recuperacion con fuente antes y despues de borrar.
- Preview y estado `enabled` de documentos cuando se implemente la ampliacion de `/admin`.
- Exclusión de documentos deshabilitados de nuevas consultas RAG.
- Abstencion cuando no hay evidencia.
- Triaje rojo sin degradacion, amarillo con alerta y ambiguo con aclaracion.
- Resumen de cierre y persistencia de alerta.
- Voz en navegador, fallback textual y comportamiento ante permisos denegados.
- Timeout de escucha, resultado parcial, no respuesta y reintento, sin inferir una decision
  clinica desde el silencio.

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
| `python -m pytest -q --basetemp <temp>` | 38 tests pasaron |
| `ruff check .` | Paso sin hallazgos |
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
