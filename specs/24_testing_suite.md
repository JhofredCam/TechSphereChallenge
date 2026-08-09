# Spec: Bateria de tests unitarios y de integracion fail-detect

**ID:** `SPEC-TEST-024`

**Estado:** `SPECIFIED`; validacion secuencial despues de `SPEC-LOG-023`

**Version:** `1.0.0`
**Fecha:** `2026-08-09`

## Objective

Construir una bateria automatizada que detecte regresiones reales en la llamada browser/API,
audio/VAD, renderizado, ciclo admin, RAG, logging propio y transformaciones de datos. La
suite debe aislar fallos actuales con oraculos observables y producir una señal de fallo
accionable, no una coleccion de mocks que siempre pasa.

La suite debe cubrir dos capas:

1. **Unitarias:** funciones puras, normalizadores, transformadores, reglas de triaje,
   VAD, serializacion/redaccion, metricas y utilidades de frontend que puedan probarse sin
   navegador ni proveedor.
2. **Integracion:** interaccion real entre FastAPI, SQLite/FTS5, servicios de llamada,
   estado del paciente/admin, RAG, eventos de voz y logger, usando dobles solo en los
   proveedores externos.

La frontera manual permanece explicita: un mock de `SpeechRecognition`, `SpeechSynthesis`,
Groq, Whisper o Chrome no aprueba G4; un test local de upload/delete no sustituye la prueba
G5 con un documento externo al corpus.

### Supuestos explicitos

1. El runtime sigue siendo Python 3.11+ con `pytest`, `pytest-cov`, Ruff y frontend HTML/CSS/
   JavaScript sin bundler. El comando primario es `python -m pytest`, no `npm test`.
2. El runner debe ejecutarse sin credenciales, red, Docker, modelos descargados ni datos
   adicionales. `GROQ_API_KEY` y Whisper se reemplazan por adaptadores falsos en integracion.
3. Cada prueba usa `tmp_path`, una instancia aislada de `Settings`, SQLite y `TestClient`;
   no se usa la instancia global de `app.main` cuando el test necesita estado temporal.
4. El dataset canonico no se copia a `tests/`. Los fixtures XLSX/PDF/TXT/MD son minimos,
   sinteticos y creados en temporales; la validacion canonica continua siendo
   `python -m scripts.validate_dataset`.
5. La spec 23 entrega el contrato de `AppLogger`. La suite debe verificar su integracion,
   pero no puede cambiar la politica de redaccion ni los niveles para hacer pasar una
   prueba.
6. La suite usa la familia permitida `Meta Llama` solo como configuracion contractualmente
   validada; no llama al proveedor real en CI/local baseline.
7. La cobertura objetivo es 80% de `app` y `scripts` con ramas, pero cualquier fallo P0
   bloquea el cierre aunque el porcentaje global sea mayor.

## Tech Stack

| Componente | Seleccion del checkout |
|---|---|
| Runtime | Python 3.11+ |
| Test runner | pytest 8.4.2 |
| Cobertura | pytest-cov 6.1.1, ramas, umbral 80% |
| Lint/sintaxis | Ruff 0.11.2 y `node --check` |
| API | FastAPI `TestClient` sobre HTTPX 0.28.1 |
| Persistencia | SQLite/FTS5 real en `tmp_path` |
| RAG | `FakeRag` o adapter falso con contrato de `SearchResult`; FTS5 real para lifecycle |
| Voz externa | cliente HTTP falso para Whisper; Web Speech queda manual |
| Frontend | contratos estaticos de HTML/JS y smoke manual en Chrome/Edge |
| Logging | `AppLogger` propio de `specs/23_custom_logging_system.md` |

## Commands

Todos los comandos se ejecutan desde la raiz. `<temp>` es un directorio escribible fuera de
`data/` y no debe versionarse.

```text
python -m pytest tests/test_logger.py tests/test_observability_contracts.py -q --basetemp <temp>/logger
python -m pytest tests/test_calls.py tests/test_timeout.py tests/test_vad.py tests/test_voice_events.py -q --basetemp <temp>/voice
python -m pytest tests/test_api.py tests/test_live_knowledge.py tests/test_http_contracts.py -q --basetemp <temp>/http
python -m pytest tests/test_data_flow_integration.py tests/test_rag_consistency.py -q --basetemp <temp>/data-rag
python -m pytest -q --basetemp <temp>/full
python -m pytest -q --basetemp <temp>/coverage --cov=app --cov=scripts --cov-branch --cov-report=term-missing --cov-fail-under=80
ruff check app scripts tests
node --check app/web/app.js app/web/voice-loop.js
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>/bootstrap
```

Los archivos nuevos de la suite deben incluirse en `testpaths` de `pyproject.toml` sin
depender de un plugin que no este declarado. Si un comando requiere un temporal distinto en
Windows, el README debe documentar el directorio escribible y conservar el mismo oraculo.

## Project Structure

```text
tests/test_logger.py                    -> niveles, schema, redaction, stack y fail-open
tests/test_observability_contracts.py   -> compatibilidad TraceRecorder/LangSmith redacted
tests/test_call_flow_integration.py     -> llamada, turnos, triaje, fuentes, resumen y metricas
tests/test_audio_vad_integration.py     -> eventos VAD, timeout, carreras e idempotencia
tests/test_data_flow_integration.py     -> upload/ingestion/RAG/delete y estados de corpus
tests/test_rendering_contracts.py       -> rutas, DOM, copy, estados y seguridad de renderizado
tests/test_admin_lifecycle.py            -> lifecycle admin ya existente, ampliado cuando aplique
tests/test_live_knowledge.py             -> aprender/olvidar sin reinicio
tests/test_vad.py                        -> algoritmo puro VAD existente
tests/test_voice_events.py               -> contrato HTTP de eventos existente
tests/fixtures/                           -> solo helpers pequenos; nunca dataset canonico
app/                                      -> codigo bajo prueba
```

Se pueden ampliar `test_api.py`, `test_call_ui_contracts.py`, `test_metrics.py` y los archivos
existentes cuando el contrato ya tiene ownership alli. No se crean dos oraculos distintos para
la misma ruta ni se mueve una prueba para ocultar una falla.

## Fail-Detect Principles

Una prueba solo es util si falla cuando se rompe la capacidad que declara proteger. Se aplican
estas reglas:

- afirmar estado final, persistencia, fuentes, metricas y eventos; no solo `status_code == 200`;
- comprobar contenido seguro y ausencia de contenido prohibido en respuestas/logs;
- usar marcadores unicos para probar aprender/olvidar y demostrar que el documento borrado no
  vuelve por cache, Chroma, snapshot ni fallback;
- probar transiciones invalidas, timeout, duplicados, errores de proveedor, revisiones stale y
  payloads vacios o mal tipados;
- no usar `pytest.mark.skip`, `xfail` ni asserts condicionales para fallos P0 sin una razon
  visible y una fecha de retiro;
- no reducir la asercion a una propiedad del mock cuando la integracion objetivo es propia;
- conservar mensajes de fallo con `call_id`, `turn_id`, estado esperado/real y recurso temporal;
- una prueba de log falla si aparece transcript, audio, prompt, API key, ruta privada o PII;
- mutar o eliminar una cita, un `turn_id`, una transicion VAD, el filtro `enabled` o el nodo
  de render debe producir al menos un test rojo de la suite.

### Prioridad de defectos

| Prioridad | Falla detectada | Accion |
|---|---|---|
| P0 | falso negativo rojo, degradacion de triaje, respuesta sin evidencia, delete con fuga, timeout convertido en turno/verde | bloquea commit y cierre |
| P1 | correlacion rota, resumen incompleto, fuente/revision perdida, secreto en log, doble turno | bloquea integracion hasta explicar |
| P2 | copy, formato secundario, error de UI no critico, compatibilidad de fixture | se registra y se corrige antes de demo |

## Testing Strategy

### Unitarias

Las unitarias no levantan servidor ni llaman proveedores. Cada caso debe tener arrange/act/assert
con un oraculo determinista.

| ID | Area | Caso fail-detect | Oraculo |
|---|---|---|---|
| `UT-LOG-01` | logger | filtra niveles y serializa JSONL estable | solo pasan niveles configurados; cada linea parsea |
| `UT-LOG-02` | seguridad | redacts claves sensibles, secretos, paths y contenido | no aparece ningun valor prohibido |
| `UT-LOG-03` | errores | captura clase y stack trace completo en `except` | nombre de funcion y linea aparecen; HTTP no lo expone |
| `UT-LOG-04` | contexto | bind de `trace_id/call_id/turn_id` no contamina otra prueba | correlacion estable y aislamiento entre contextos |
| `UT-DATA-01` | transformadores | parsea JSON embebido, IDs, capas y joins | rechaza hoja/header/capa invalidos |
| `UT-DATA-02` | ingestion | rutas recursivas, espacios, duplicados, hash y PDF sin texto | status `available`/`needs_ocr` correcto |
| `UT-RAG-01` | retrieval | relevancia, revision y filtro enabled | solo devuelve chunks autorizados |
| `UT-RAG-02` | seguridad RAG | abstencion, inyeccion y salida sin cita | no inventa dosis/diagnostico ni omite limite |
| `UT-VAD-01` | audio | umbral, histéresis, silencio y texto confirmado | silencio vacio nunca finaliza turno |
| `UT-VAD-02` | estados | doble finalizacion y `onend` tardio | una sola transicion/submit |
| `UT-TRIAGE-01` | triaje | rojo/yellow sticky y unknown | nivel no baja y ambiguedad pregunta |
| `UT-MET-01` | metricas | timestamps invalidos, percentiles y consumo | no fabrica latencia ni duplica eventos |
| `UT-UI-01` | render | estados y copy se insertan con `textContent`/safe DOM | no ejecuta markup de datos |

### Integracion de servicios y API

Estas pruebas usan servicios propios reales y sustituyen solo sistemas externos o costosos.

| ID | Flujo | Dobles permitidos | Aserciones obligatorias |
|---|---|---|---|
| `IT-CALL-01` | iniciar llamada -> turno -> respuesta -> cierre | `FakeAgent` o adapter LLM | filas de llamada/turno, nivel, alert, fuentes, resumen, `events.jsonl` y `app.log.jsonl` |
| `IT-CALL-02` | rojo/yellow/unknown en llamada | ninguno para triaje | sticky level, alerta persistente y pregunta de aclaracion |
| `IT-AUDIO-01` | VAD -> `PROCESSING` -> final -> audio timing | cliente STT falso solo para `/audio` | estados, `listen_id`, `client_turn_id`, una solicitud y sin transcript en voice-events |
| `IT-AUDIO-02` | timeout, parcial tardio, retry y duplicado | reloj controlado | `409`/estado seguro, sin turno clinico ni verde artificial |
| `IT-RAG-01` | upload -> consulta grounded -> delete -> consulta | FTS5 real; Chroma fake opcional | fuente/pagina antes, abstencion y ausencia de fuente despues sin reiniciar |
| `IT-ADMIN-01` | listar/preview/disable/enable/delete | filesystem temporal | estados visibles, no fuga de `stored_path`, filtro `enabled` y limpieza |
| `IT-DATA-01` | bootstrap temporal completo | XLSX/PDF fixture minimo | conteos, joins, `needs_ocr`, idempotencia y ningun cambio a `dataset/` |
| `IT-HTTP-01` | errores 4xx/5xx y payloads limite | providers falsos | contrato de error seguro, evento `request_failed` y stack solo en log |
| `IT-LOG-01` | instrumentacion end-to-end | sink temporal | entrada/salida, estado, RAG, voz y excepcion comparten correlacion |
| `IT-MET-01` | `/api/metrics` despues de llamada | reloj/timestamps controlados | P50/P95, tokens, model calls, RAG queries y calls concilian con events |
| `IT-RENDER-01` | contrato de `/`, `/patient`, `/admin`, `/call` | ninguno | archivos existen, rutas cargan, selectores/labels/estados esperados y JS parsea |

`FakeAgent`, `FakeRag`, `FakeAdapter`, reloj controlado y cliente HTTP falso deben implementar
el mismo contrato publico que reemplazan. No se mockea `CallService`, `DocumentService`,
`RagService` FTS5, SQLite, serializacion de respuesta ni el logger cuando son el objeto de
la prueba.

### Browser y evidencia manual

| ID | Capacidad | Metodo | Estado |
|---|---|---|---|
| `MAN-VOICE-01` | permiso, microfono, `es-CO`, escucha y respuesta TTS | Chrome/Edge real en `127.0.0.1` | manual; no reemplazable por mock |
| `MAN-VOICE-02` | VAD continuo, pausa, ruido y retorno `RESPONDING -> LISTENING` | navegador y microfono reales | manual |
| `MAN-ADMIN-01` | inventario, preview y estados visibles | navegador real | manual complementario a HTTP |
| `MAN-G5-01` | documento externo aprendido y olvidado sin reinicio | `/admin` + `/call` reales | compuerta G5; pendiente hasta ejecutar |

Los tests de contrato estatico pueden detectar un selector o mensaje ausente, pero nunca
declaran que el microfono o el audio funcionen. Las etiquetas `MANUAL_PENDING`, `TESTED` y
`FAILED` deben mantenerse en el informe y bitacora.

## Fixtures, isolation y mocks

- `tmp_path` para base, uploads, JSONL, logs, PDFs y XLSX;
- `Settings(data_dir=tmp_path)` y `init_database(settings)` para cada escenario;
- `create_app(settings=settings, database=database)` y `with TestClient(application)`;
- `monkeypatch.delenv` para `GROQ_API_KEY`, LangSmith y endpoints remotos;
- `FakeAgent` que devuelva respuestas con fuente valida, abstencion y error controlado;
- `FakeRag` con revision, `SearchResult` y un contador de consultas;
- `FakeAdapter` que permita respuesta valida, cita invalida, contenido inseguro y timeout;
- cliente falso de Whisper con `raise_for_status`, JSON valido, JSON invalido y error de red;
- reloj monotono/UTC controlado para latencia, timeout y percentiles;
- contenido unico como `marcador lunar 92817`, nunca informacion del paciente real;
- fixtures de PDF con texto y sin capa, TXT/MD anidados con espacios/Unicode y XLSX con hoja
  `result` y JSON embebido;
- no compartir estado entre pruebas ni depender del orden, IDs aleatorios o `data/` global;
- cerrar `database`, `TestClient`, streams y clientes falsos en `finally`.

## Coverage and quality gates

La suite se considera verde solo si se cumplen todas las condiciones:

- todas las unitarias e integraciones P0 pasan;
- `python -m pytest -q --basetemp <temp>/full` termina sin skips silenciosos;
- cobertura de `app` y `scripts` >= 80% con ramas, excluyendo solo codigo generado o
  platform-specific justificado;
- `ruff check app scripts tests` sin hallazgos;
- `node --check app/web/app.js app/web/voice-loop.js` valido;
- `python -m scripts.validate_dataset` conserva los conteos `3991/40/40/160` del dataset
  canonico cuando se ejecuta con sus archivos locales;
- no se commitean `data/`, logs, XML de cobertura, snapshots ni credenciales;
- una capacidad manual queda marcada como manual aunque todos los mocks pasen.

La cobertura no puede justificar la eliminacion de una asercion. Las pruebas de borrado,
abstencion, falso negativo, timeout, redaccion y no duplicacion son obligatorias aunque
cuesten mas que una prueba de happy path.

## Code Style

```python
def test_delete_removes_live_knowledge_without_restart(client, marker):
    upload = client.post("/api/admin/documents", files={"file": ("probe.txt", marker, "text/plain")})
    assert upload.status_code == 200
    document_id = upload.json()["id"]

    before = client.post(f"/api/calls/{call_id}/turns", json={"text": marker}).json()
    assert before["grounded"] is True
    assert before["source_ids"]

    deleted = client.delete(f"/api/admin/documents/{document_id}")
    assert deleted.status_code == 200

    after = client.post(f"/api/calls/{call_id}/turns", json={"text": marker}).json()
    assert after["abstained"] is True
    assert marker not in json.dumps(after, ensure_ascii=False)
```

El caso muestra el patron esperado: estado, evidencia positiva, mutacion, ausencia y
seguridad. En el codigo real se usan datos temporales y un `call_id` creado dentro del
fixture; nunca se depende de una variable global o del dataset canonico.

## Boundaries

- **Always:** probar primero el caso P0, aislar datos/credenciales, validar respuestas y
  persistencia, comprobar eventos/logs, usar mensajes de fallo accionables, ejecutar el
  focused test y luego la suite completa antes del commit.
- **Ask first:** agregar Playwright/Selenium, paralelizar SQLite en Windows, cambiar el
  umbral de cobertura, introducir un proveedor real en pruebas automaticas, modificar
  schema de base o cambiar el modelo permitido.
- **Never:** commitear secretos/logs/datos locales, usar el `label_ground_truth` como
  contexto clinico, ocultar un fallo con `skip/xfail`, afirmar G4/G5 desde mocks, borrar una
  prueba P0 para subir cobertura o copiar `dataset/`/`docs/` a fixtures.

## Success Criteria

| ID | Criterio verificable | Evidencia |
|---|---|---|
| `TEST-AC-01` | `python -m pytest -q --basetemp <temp>/full` ejecuta unitarias e integraciones sin credenciales | salida fechada |
| `TEST-AC-02` | funciones puras, transformadores, hooks/utilidades VAD y render contracts tienen oraculos de fallo | tests unitarios |
| `TEST-AC-03` | `/call` integra llamada, estado paciente, triaje, fuentes, resumen y metricas con servicios reales | `IT-CALL-*` |
| `TEST-AC-04` | audio/VAD prueba estados, silencio, timeout, carreras, idempotencia y no transcript en eventos | `IT-AUDIO-*` |
| `TEST-AC-05` | admin/RAG prueba upload, disponibilidad, consulta, delete y olvido sin reinicio | `IT-RAG-01` + `IT-ADMIN-01` |
| `TEST-AC-06` | logging prueba niveles, redaccion, correlacion, stack trace y fail-open | `UT-LOG-*` + `IT-LOG-01` |
| `TEST-AC-07` | datos prueban hoja `result`, JSON, joins, capas, rutas problematicas, PDF escaneado e idempotencia | `UT-DATA-*` + `IT-DATA-01` |
| `TEST-AC-08` | renderizado verifica rutas, copy, estados y no ejecucion de markup sin declarar G4 | `UT-UI-01` + `IT-RENDER-01` |
| `TEST-AC-09` | coverage de ramas >= 80%, Ruff y Node check pasan sin artefactos generados versionados | comandos de calidad |
| `TEST-AC-10` | los casos P0 fallan de forma demostrable ante regresiones de cita, delete, triaje, timeout o fuga | mutacion/revision de oraculos |
| `TEST-AC-11` | G2/G4/G5 se reportan honestamente como evidencia automatizada o manual | bitacora/informe |

## Implementation Plan and Tasks

1. Congelar el contrato de `specs/23_custom_logging_system.md` y agregar sus fixtures
   unitarios de logger.
2. Crear o ampliar tests de VAD, llamadas, audio events, UI contracts y datos sin solaparse
   con la autoridad de cada servicio.
3. Crear integraciones con `TestClient`, SQLite/FTS5 y filesystem temporal; aislar Groq,
   Whisper, Chroma y reloj donde corresponda.
4. Ejecutar focused suites y corregir primero P0/P1. No cambiar produccion solo para
   satisfacer un assert incorrecto: actualizar la spec si cambia el contrato.
5. Ejecutar suite completa, cobertura, Ruff, Node check y validacion del dataset.
6. Registrar comando, fecha, commit, entorno, conteos, pendientes manuales y cualquier
   limitacion en `readme/06_bitacora_de_sesiones/` y `readme/04_metricas_y_evidencia.md`.

## Dependencies and execution order

```text
Batch 8: Spec 23 custom logger (contrato + instrumentacion)
                 |
                 v
Batch 9: Spec 24 fail-detect (unitarias + integracion + regresion completa)
                 |
                 v
        evidencia G2/G4/G5 y cierre del informe
```

Spec 24 puede preparar fixtures puros en paralelo con la primera parte de Spec 23, pero no
se integra ni se declara verde hasta que el contrato del logger y los eventos instrumentados
estabilicen nombres, redaccion y correlacion.

## Open Questions

1. Si la suite debe automatizar DOM y microfono de forma reproducible, hay que aprobar
   Playwright o un conector de navegador; el primer corte conserva el runner estatico y el
   smoke manual para proteger el setup de 15 minutos.
2. La matriz no fija pytest-xdist: antes de paralelizar deben resolverse locks de SQLite,
   handles Windows y escritura concurrente de JSONL.
3. La cobertura de hooks JavaScript se limita al contrato estatico hasta contar con un runner
   frontend aprobado; no se presenta como cobertura de ejecucion en navegador.
