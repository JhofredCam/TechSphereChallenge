# Informe final - estado del MVP

> **Estado:** corte honesto al 2026-08-08. La implementacion local y la evidencia
> automatizada estan verificadas. Los valores de voz real, capturas, video, cronometraje y
> demo externa marcados como `PENDIENTE` no se presentan como mediciones ni como aprobacion
> de una compuerta.

## 1. Resumen ejecutivo

**Problema:** el seguimiento postoperatorio necesita recoger sintomas en lenguaje cotidiano,
responder con conocimiento trazable y escalar senales de alarma sin depender de telefonia real.

**Solucion:** una aplicacion local FastAPI/Uvicorn con `/admin` para gestionar documentos y
`/call` para una llamada browser/API. SQLite/FTS5 recupera fuentes, el triaje determinista
conserva alertas, el agente responde en espanol con cita o abstencion y el cierre guarda un
resumen estructurado.

**Resultado:** runtime local implementado. Pasaron 96 tests, Ruff no reporto hallazgos, el
dataset fue validado y el bootstrap proceso el corpus local. Preview/toggle/timeout tienen
pruebas locales; la demo manual de voz, el cronometraje G2, Groq/Whisper real y la evidencia G5
con documento externo siguen pendientes.

## 2. Alcance y limites

El MVP busca una aplicacion web local para seguimiento postoperatorio en espanol de pacientes
colombianos. Incluye:

- Consola para subir, listar, previsualizar, habilitar/deshabilitar y eliminar documentos con
  estado tecnico y publicacion visibles.
- Llamada desde navegador/API con microfono, transcripcion, respuesta y audio.
- Recuperacion trazable desde el corpus local, solo con `status='available' AND enabled=1`.
- Timeout total configurable por turno, estados de escucha, reintento/texto, `listen_id`,
  `client_turn_id` y `late_transcript`.
- Triaje conservador, alerta persistente y resumen de llamada.
- Metricas de latencia, consumo, recuperacion y costo.

No incluye telefonia real, integracion hospitalaria, autenticacion empresarial ni cobertura
clinica universal. El dataset es sintetico y no esta validado para uso asistencial.

## 3. Modelo y stack

### Declaracion obligatoria

La familia seleccionada para el razonamiento del agente es **Meta Llama**, una familia
permitida por el reto.

| Componente | Seleccion | Estado |
|---|---|---|
| Razonamiento principal | `llama-3.1-8b-instant` via Groq | Configurado; uso remoto en vivo PENDIENTE |
| Familia | Meta Llama | Permitida por [`docs/stack-tecnico.md`](stack-tecnico.md) |
| STT opcional | `whisper-large-v3` via Groq | No es el modelo de razonamiento; camino implementado, prueba remota PENDIENTE |
| TTS | `SpeechSynthesis` del navegador | Integrado en `/call`; prueba manual PENDIENTE |
| Recuperacion | SQLite FTS5 lexical | Implementada y cubierta por tests locales |
| Extraccion PDF | PyMuPDF | Implementada; bootstrap clasifica `needs_ocr` |

**Razon de eleccion:** `llama-3.1-8b-instant` pertenece a la familia Meta Llama permitida,
esta expuesto por el adaptador OpenAI-compatible de Groq y es apropiado para una respuesta
breve de baja latencia. SQLite FTS5 reduce dependencias, permite citas por documento/pagina/
chunk y hace atomicos el borrado y la invalidacion local. El proveedor remoto no se ejercito
en esta sesion; por eso el camino efectivo de demo y sus costos siguen pendientes.

Si `llama-3.1-8b-instant` fue retirado, registrar el sucesor vigente dentro de Meta Llama/Groq
y actualizar configuracion, setup y video juntos. No declarar un modelo de otra familia.

## 4. Datos y preparacion

- Fuentes: [`dataset/`](../dataset/) y [`dataset/textos/`](../dataset/textos/), sin copias.
- Comando de validacion: `python -m scripts.validate_dataset`.
- Join: `paciente_id` entre perfiles y `caso_id = "caso_" + trayectoria_id` entre
  conversaciones y trayectorias.
- Separacion de capas: filtrar `capa1_limpia` o `capa2_ruidosa` antes de reconstruir una
  conversacion.
- PDF escaneado: estado `needs_ocr`, no disponible hasta contar con texto extraible.

**Resultado de validacion (2026-08-08):** `dataset validation: valid`; los cuatro XLSX
reportaron `3991`, `40`, `40` y `160` filas. La validacion es de solo lectura y el bootstrap
no modifica las fuentes canonicas. El bootstrap proceso 104 documentos del corpus, con 103
`available` y 1 `needs_ocr`; la segunda ejecucion no reproceso el contenido ya indexado.

## 5. Arquitectura y comportamiento

Consultar [arquitectura.md](arquitectura.md) y la [vista formal derivada](../mvp/deliverables/02_architecture/architecture.md).
La implementacion demuestra localmente que:

1. El triaje determinista puede elevar y conservar el nivel, pero nunca degradar rojo.
2. El agente solo redacta respuestas clinicas con evidencia recuperada y cita trazable.
3. Una consulta sin evidencia produce abstencion explicita.
4. Preview inspecciona `pages.text`; disable conserva el documento pero lo excluye del RAG,
   enable lo recupera sin reingesta y delete cambia el conocimiento disponible sin reiniciar.
5. La escucha publica su timeout por `/health`, no convierte parcial/timeout en turno y evita
   duplicados mediante `listen_id`/`client_turn_id`.
6. El cierre persiste paciente, procedimiento, sintomas, decision, fuentes, alerta y pasos.

**Correspondencia con codigo:** verificada en `app/main.py`, `app/database.py`, los servicios
de `app/services/` y las pruebas de API, ingestion, agente, triaje, llamadas, metricas y
conocimiento vivo. El smoke de voz en navegador y la prueba G5 con documento externo siguen
pendientes.

### Especificaciones y estado sincronizado

- [Estructura de entregables](../specs/03_mvp_structure_specification.md): fases aplicadas bajo
  `mvp/crisp-dm/` y entregables bajo `mvp/deliverables/`; preflight estructural verificado.
- [Ciclo documental de `/admin`](../specs/04_admin_document_lifecycle_specification.md):
  preview textual, `enabled`, `rag_eligible`, habilitar, deshabilitar, snapshots y delete;
  runtime y pruebas locales verificados.
- [Timeout de escucha](../specs/05_patient_listening_timeout_specification.md):
  `PATIENT_LISTEN_TIMEOUT_MS`, estados, eventos, reintento, `client_turn_id`, `listen_id` y
  `late_transcript`; runtime y pruebas locales verificados.
- [Diagrama integrador](../specs/06_system_flow_diagram_specification.md): ASCII, Mermaid,
  contratos y matriz `TRZ-*` sincronizados con las tres specs anteriores.
- [Pruebas unitarias e integracion](../specs/07_testing_unit_integration_specification.md):
  estrategia ejecutable, cobertura branch `80.07%` y frontera manual conservada.

G2, G4, G5 externo, Groq/Whisper real y las metricas de voz/costo siguen pendientes de evidencia
manual; las pruebas locales no cambian esos estados.

## 6. Configuracion y prompts

Valores configurados en el codigo, sin incluir secretos:

| Elemento | Valor / enlace | Estado |
|---|---|---|
| Modelo y version | `llama-3.1-8b-instant` via Groq | Configurado; familia verificada, llamada remota PENDIENTE |
| Temperatura y limites | `temperature=0.0`, `max_tokens=220` | Implementado en `app/services/agent.py` |
| Prompt de sistema | `AgentService._system_prompt()` en `app/services/agent.py` | Implementado; delimita fuentes como datos no ejecutables |
| Formato de citas | filename, pagina, chunk, score, `corpus_revision` | Implementado y cubierto por tests |
| Regla de abstencion | Sin evidencia actual, evidencia insegura o inyeccion: explicar limite y no inventar | Implementado y cubierto por tests |
| Regla de triaje | `classify_triage` y `highest_level` en `app/services/triage.py` | Implementado; rojo/amarillo no degradan |
| Timeout y reintentos | Groq chat 12 s; Whisper 30 s; fallback extractivo sin reintento inseguro | Implementado |
| Ciclo admin | `enabled`, `rag_eligible`, preview <=8000, snapshots y filtro RAG | Implementado y cubierto por `tests/test_admin_lifecycle.py` |
| Escucha del paciente | `PATIENT_LISTEN_TIMEOUT_MS=30000`, default/rango y `/health` publico | Implementado y cubierto por `tests/test_timeout.py`; smoke browser PENDIENTE |
| Idempotencia de escucha | `listen_id`, `client_turn_id`, duplicate y `409 late_transcript` | Implementado y cubierto por `tests/test_timeout.py` |

## 7. Metricas

La [guia de metricas y evidencia](../readme/04_metricas_y_evidencia.md) define las
formulas. Completar solo con valores respaldados por logs.

| Metrica | Valor | Muestra / entorno | Artefacto |
|---|---:|---|---|
| Latencia P50 (ms) | PENDIENTE | No hubo smoke de voz real | `MetricsService`; test de percentiles |
| Latencia P95 (ms) | PENDIENTE | No hubo smoke de voz real | `MetricsService`; test de timestamps |
| Tokens entrada por turno | PENDIENTE | No hubo llamada remota real | Contrato JSONL y tests |
| Tokens salida por turno | PENDIENTE | No hubo llamada remota real | Contrato JSONL y tests |
| Tokens entrada/salida por llamada | PENDIENTE | No hubo llamada remota real | `/api/metrics` implementado |
| Invocaciones al modelo por turno | PENDIENTE | Fallback local en pruebas | Campo `model_calls` y tests |
| Consultas RAG por llamada | PENDIENTE | Pruebas locales, sin demo final | Campo `rag_queries` y tests |
| Costo estimado por llamada | PENDIENTE | Falta precio vigente y muestra real | Formula documentada |

Formula a completar con precios y fecha:

```text
costo_llamada = (tokens_entrada / 1_000_000 * precio_entrada) +
                 (tokens_salida / 1_000_000 * precio_salida)
```

## 8. Evaluacion y compuertas

| Gate | Evidencia | Estado |
|---|---|---|
| G1 | Repositorio, diagrama, informe y video | PENDIENTE; falta video de entrega |
| G2 | Setup limpio en <=15 minutos siguiendo README | `MANUAL_PENDING`: falta cronometraje desde entorno limpio |
| G3 | Familia/modelo permitido y declarado | `TESTED` local en configuracion, codigo y tests: Meta Llama / `llama-3.1-8b-instant`; uso remoto `MANUAL_PENDING` |
| G4 | Saludo y pregunta trivial con audio de ida y vuelta | `MANUAL_PENDING`: falta smoke manual con microfono/audio; no se infiere de mocks |
| G5 | Upload, preview, uso, disable/enable, delete y olvido sin reinicio | `TESTED` local; `MANUAL_PENDING` para documento externo en demo |

### Resultados de pruebas

| Prueba | Comando / recorrido | Resultado | Fecha |
|---|---|---|---|
| Dataset | `python -m scripts.validate_dataset` | Valido: `3991/40/40/160` | 2026-08-08 |
| Admin/timeout | `python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>` | 24 tests pasaron | 2026-08-08 |
| Suite | `python -m pytest -q --basetemp <temp>` | 96 tests pasaron | 2026-08-08 |
| Calidad | `ruff check .` | Paso sin hallazgos | 2026-08-08 |
| Sintaxis web | `node --check app/web/app.js` | Valida | 2026-08-08 |
| Bootstrap | `python -m app.bootstrap --data-dir <temp>` | 104 documentos: `available=103`, `needs_ocr=1` | 2026-08-08 |
| Idempotencia | Test de bootstrap dentro de la suite | Paso; segunda ejecucion sin reprocesar contenido | 2026-08-08 |
| Conocimiento vivo | `tests/test_live_knowledge.py` dentro de la suite | Upload/search/delete local verificado sin reinicio | 2026-08-08 |
| Voz | `/call` en Chrome/Edge | PENDIENTE de smoke manual con microfono/audio | PENDIENTE |
| Setup | [setup local](../readme/02_setup_local.md) cronometrado | PENDIENTE de entorno limpio | PENDIENTE |

## 9. Demo y trazabilidad

Enlazar aqui capturas, logs y video reales. El estado actual es:

- Demo de `/admin`: implementada; captura `PENDIENTE`.
- Documento nuevo recuperado con cita: verificado en prueba local; documento externo en demo `PENDIENTE`.
- Documento eliminado y no recuperable: verificado en prueba local sin reinicio; captura `PENDIENTE`.
- Intercambio de voz en espanol: `PENDIENTE` de smoke manual.
- Abstencion sin evidencia: cubierta por tests; captura de demo `PENDIENTE`.
- Alerta y resumen de cierre: cubiertos por tests; captura de demo `PENDIENTE`.
- Respuesta de `/api/metrics`: endpoint y agregacion implementados; log de llamada real `PENDIENTE`.

## 10. Riesgos y limitaciones

- Los datos son sinteticos y no clinicamente validados.
- Un PDF escaneado sin OCR no es conocimiento disponible.
- FTS5 lexical puede perder sinonimos o regionalismos; embeddings BGE-M3 quedan como
  evolucion, no como requisito de este corte.
- SpeechRecognition y SpeechSynthesis dependen del navegador y de permisos.
- Groq, cuotas y disponibilidad del identificador del modelo requieren verificacion en una
  demo con credencial; el fallback local no demuestra el uso remoto.
- El canal de alerta es local y persistente; no sustituye personal capacitado ni envia SMS,
  correo o notificacion hospitalaria.

## 11. Preguntas de cierre del video

### Pregunta 1

**Problema, solucion y valor diferencial:** [Responder con evidencia de la demo, no solo
con intencion de diseno.]

### Pregunta 2

**Decision tecnica relevante, alternativas, riesgos y mejora en dos semanas:** [Completar.
Una opcion coherente con este MVP es explicar SQLite FTS5 + triaje determinista + Llama
permitido frente a embeddings o un modelo local, indicando que se midio y que aun no.]

## 12. Cierre y aprobacion

- [x] Modelo exacto y familia verificados contra configuracion y tests; falta log de una
  llamada remota real.
- [ ] Setup cronometrado y <=15 minutos.
- [ ] G4 verificada con voz real.
- [ ] G5 verificada con documento fuera del corpus.
- [ ] Metricas de una llamada real llenas y reproducibles.
- [ ] Video y capturas corresponden al commit entregado.
- [x] Limitaciones y pendientes estan explicitados; falta la revision final responsable.

Responsable: `PENDIENTE`
Commit evaluado: `PENDIENTE` (checkout de trabajo sin commit de cierre)
Fecha de corte: `2026-08-08`
Fecha de cierre: `PENDIENTE`
