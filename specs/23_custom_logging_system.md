# Spec: Sistema de logging propio y trazabilidad end-to-end

**ID:** `SPEC-LOG-023`

**Estado:** `SPECIFIED`; pendiente de implementacion y evidencia

**Version:** `1.0.0`
**Fecha:** `2026-08-09`

## Objetivo

Implementar una capa de logging propia, centralizada y estructurada para el MVP de
seguimiento postoperatorio. El logger debe permitir reconstruir el recorrido de una
peticion, una llamada, un turno y una consulta RAG sin depender unicamente de la salida
de consola ni del exporter opcional de LangSmith.

El resultado debe servir para:

- diagnosticar fallos de llamada, audio, VAD, RAG, ingestion y API;
- conciliar las metricas obligatorias de la rubrica con eventos observables;
- identificar estados y transiciones sin guardar audio, transcript completo ni PII;
- conservar el stack trace completo de errores en el artefacto local de diagnostico;
- demostrar que el modelo declarado, el perfil RAG y los servicios se inicializaron con
  configuracion efectiva y secretos redactados.

El logger no cambia las decisiones de triaje, la elegibilidad de fuentes, el contrato de
voz ni la autoridad de SQLite. Un fallo del sink de logs tampoco puede descartar una
llamada clinica ya persistida ni convertir un error en una respuesta exitosa.

### Supuestos explicitos

1. El checkout continua siendo una aplicacion Python 3.11+ con FastAPI y un grafo de
   servicios creado en `app.main.create_app()`.
2. El modulo canonico sera `app/services/logger.py`; `MetricsService` conservara
   `data/events.jsonl` como fuente de metricas. El logger usara un archivo separado,
   por defecto `data/app.log.jsonl`, para no mezclar eventos de diagnostico con turnos.
3. La persistencia local y la consola son sinks del mismo contrato propio. La consola
   es util para desarrollo, pero el archivo JSONL es el artefacto minimo de trazabilidad.
4. Los datos del reto son sinteticos. Aun asi, se aplica una politica de minimizacion:
   ningun log escribe por defecto nombre, paciente, procedimiento, transcript, texto de
   chunks, audio, prompt, token de acceso, ruta privada ni contenido de archivo.
5. `call_id`, `turn_id`, `listen_id` y `trace_id` son correladores internos permitidos
   en el log local; el exporter externo debe conservar la redaccion/hash ya definida en
   `app.services.observability`.
6. El modelo de razonamiento sigue siendo `llama-3.1-8b-instant` via Groq cuando esta
   configurado, perteneciente a la familia Meta Llama permitida. El logger no introduce
   otro modelo ni proveedor.
7. El primer corte no necesita un agregador remoto, una cola ni un daemon adicional. La
   rotacion local y la escritura append-only deben funcionar sin red y dentro del setup
   de 15 minutos.

## Tech Stack y contrato

| Componente | Decision |
|---|---|
| Lenguaje | Python 3.11+ con tipos explicitos |
| Modulo propio | `app/services/logger.py` |
| Serializacion | JSON UTF-8, una entrada por linea, `ensure_ascii=False` y orden estable |
| Persistencia | `data/app.log.jsonl`, ignorado por Git, con rotacion por tamano |
| Consola | Salida legible derivada del mismo evento; no es la unica fuente |
| Contexto | `contextvars` o equivalente para `trace_id`, `call_id`, `turn_id` y `request_id` |
| Redaccion | Allowlist de campos, claves sensibles y paths privados bloqueados |
| Integracion existente | `MetricsService`, `TraceRecorder` y health permanecen compatibles |
| Dependencias | Biblioteca estandar; no agregar servicio obligatorio |

### API propuesta

El contrato publico debe ser pequeno y estable. Los nombres siguientes son normativos; la
implementacion puede usar clases auxiliares privadas.

```python
from enum import StrEnum
from typing import Any, Mapping


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class AppLogger:
    def log(
        self,
        level: LogLevel,
        event: str,
        *,
        message: str,
        fields: Mapping[str, Any] | None = None,
        error: BaseException | None = None,
    ) -> dict[str, Any]: ...

    def bind(self, **context: Any) -> "AppLogger": ...
    def exception(self, event: str, *, message: str, error: BaseException,
                  fields: Mapping[str, Any] | None = None) -> dict[str, Any]: ...


def configure_logger(settings: Any) -> AppLogger: ...
```

Cada evento debe tener como minimo:

```json
{
  "event_id": "log_...",
  "created_at": "2026-08-09T12:00:00.000Z",
  "level": "INFO",
  "event": "call_state_changed",
  "service": "calls",
  "operation": "record_voice_event",
  "trace_id": "trace_...",
  "call_id": "call_...",
  "turn_id": null,
  "message": "estado de llamada actualizado",
  "fields": {
    "from_state": "LISTENING",
    "to_state": "PROCESSING",
    "payload_type": "VoiceEventRequest",
    "payload_keys": ["event_type", "listen_id"],
    "payload_size": 128
  },
  "duration_ms": 3.2
}
```

Los campos reales pueden omitir valores nulos, pero nunca deben omitir `level`, `event`,
`created_at`, `service` y el correlador disponible. Un evento de error agrega:

```json
{
  "error": {
    "class": "ValueError",
    "message": "mensaje seguro y redactado",
    "stack_trace": "Traceback ... completo ..."
  }
}
```

`stack_trace` se obtiene con `traceback.format_exc()` dentro del `except` y se redactan
paths, tokens y valores sensibles sin truncar las lineas necesarias para diagnosticar el
origen. La respuesta HTTP puede ser breve y segura; el log local conserva el stack trace.

### Niveles

| Nivel | Uso | Ejemplos |
|---|---|---|
| `DEBUG` | detalle tecnico opt-in | tipos, tamanos, hashes cortos, decisiones de fallback |
| `INFO` | eventos normales auditables | inicializacion, upload procesado, estado de llamada, RAG con fuentes |
| `WARN` | degradacion segura o datos incompletos | timeout, fallback extractivo, exporter caido, PDF `needs_ocr` |
| `ERROR` | fallo que requiere diagnostico | excepcion capturada, transicion rechazada, sink no disponible |

El filtrado por nivel se aplica al sink, no elimina la capacidad de crear el evento. Los
errores P0 de seguridad, persistencia o trazabilidad no se silencian por estar configurado
el nivel `INFO`.

## Configuracion y sinks

Agregar al contrato de entorno, con valores publicos y sin secretos:

```text
APP_LOG_LEVEL=INFO
APP_LOG_PATH=data/app.log.jsonl
APP_LOG_CONSOLE=true
APP_LOG_MAX_BYTES=5242880
APP_LOG_BACKUP_COUNT=3
APP_LOG_DEBUG_SAMPLE_RATE=1.0
```

Requisitos:

- validar nivel, tamano y contador con limites finitos antes de iniciar el servidor;
- crear solo el directorio de datos configurado, nunca una ruta tomada del payload;
- escribir una linea atomica con lock de proceso para los workers soportados por el perfil;
- rotar por tamano sin borrar `events.jsonl`, la base SQLite ni uploads;
- si el archivo no puede escribirse, emitir una alerta minima a stderr y continuar el
  request; el contador de eventos descartados debe ser visible en health o metricas;
- `APP_LOG_CONSOLE=false` no debe desactivar la persistencia local;
- no leer ni volcar `.env`, `GROQ_API_KEY`, `LANGCHAIN_API_KEY` u otros secretos. La
  inicializacion registra solo nombre de variable, presencia booleana y configuracion
  efectiva redacted.

## Correlacion y trazabilidad

El contexto se crea en cada entrada de API, tarea de bootstrap y llamada. Si el cliente no
manda `request_id`, se genera uno. `trace_id` permanece estable durante una operacion y
`call_id`, `turn_id` y `listen_id` se agregan cuando existen. Las funciones puras pueden
recibir un contexto explicito en vez de depender de estado global.

Los eventos deben permitir buscar al menos estas relaciones:

```text
request_id / trace_id
  -> call_id
     -> listen_id + VAD/audio state
        -> turn_id
           -> RAG retrieval + source_ids + corpus_revision
              -> response metrics + audio timing
```

No se guardan transcript, audio ni texto de chunks para lograr esa relacion. Para payloads
se registra tipo, claves permitidas, tamano, conteo, estado, hash corto no reversible y
resultado de validacion. Para fuentes se registran `source_ids`, filename snapshot solo si
la politica local lo permite, pagina, revision y cantidad; el contenido queda fuera.

## Puntos de instrumentacion obligatorios

La instrumentacion debe cubrir entradas, salidas y excepciones. Cada wrapper debe registrar
duracion monotona y no duplicar un mismo error en varios niveles sin indicar su origen.

| Area | Eventos minimos | Campos seguros |
|---|---|---|
| Configuracion e inicio | `config_loaded`, `service_initialized`, `startup_completed` | perfil, modelo/familia, backends, versiones, presencia de secrets |
| API | `request_started`, `request_completed`, `request_rejected`, `request_failed` | metodo, ruta normalizada, status, tipo/tamano de payload, duracion |
| Funciones clave | `function_entered`, `function_returned`, `function_failed` | modulo, funcion, tipos, claves, estado, duracion, resultado resumido |
| Admin/documentos | `document_upload_started`, `document_processed`, `document_deleted`, `document_state_changed` | extension, sha256, paginas/chunks, estado, revision, duracion |
| Ingestion | `loader_started`, `loader_completed`, `ocr_required`, `chunking_completed` | formato, paginas, chunks, bytes, hash, `needs_ocr` |
| Llamada | `call_started`, `call_state_changed`, `turn_started`, `turn_completed`, `call_finished` | ids, estados, nivel de triaje, alert, contador de turnos, duracion |
| Audio/VAD | `audio_started`, `audio_finished`, `vad_state_changed`, `voice_event_rejected`, `stt_fallback` | implementation, locale `es-CO`, `listen_id`, estado, elapsed, error_code; nunca audio/texto |
| RAG | `rag_query_started`, `rag_query_completed`, `rag_fallback`, `rag_abstained` | backend, revision, query hash, `rag_queries`, hit count, source ids, scores agregados, duracion |
| Modelo | `llm_started`, `llm_completed`, `llm_fallback`, `llm_rejected` | familia, version, provider, tokens, model calls, razon segura |
| Errores | `exception_captured`, `persistence_failed`, `observability_degraded` | clase, operacion, stack trace redacted, retryable, correladores |

La lista es end-to-end: `app/main.py`, `app/bootstrap.py`, `app/config.py`,
`app/services/documents.py`, `ingestion.py`, `calls.py`, `agent.py`, `rag.py`,
`rag_chain.py`, `voice.py`, `vad.py`, `metrics.py` y `observability.py` deben usar el
logger central o un adapter compatible. No se permite crear un logger ad-hoc por modulo.

### Estados de llamada y audio

Las transiciones minimas que deben quedar visibles son:

```text
IDLE -> LISTENING -> PROCESSING -> RESPONDING -> LISTENING
                         |              |
                         +-> ERROR      +-> ENDED
```

Tambien se registran `PARTIAL`, `NO_RESPONSE`, `LISTEN_TIMEOUT`, `RECOGNITION_ERROR` y
`RETRY_REQUIRED` como estados de intento. Un parcial o un silencio no crean un turno
clinico. El logger registra el hecho y sus ids, no el texto parcial.

### RAG y respuesta

Cada respuesta debe poder conciliarse con:

- la revision de corpus observada antes y despues de la consulta;
- el backend usado (`fts5`, `chroma` u otro adapter permitido);
- cantidad de consultas, hits y fuentes, con sus ids y paginas;
- si hubo abstencion, fallback, inyeccion ignorada o proveedor no disponible;
- `input_tokens`, `output_tokens`, `model_calls`, `model_version` y latencia;
- el evento de audio correspondiente cuando la respuesta se reproduce.

No se debe registrar la pregunta completa, el prompt ni el contexto recuperado. Un hash
corto y la cantidad de tokens/palabras estimada son suficientes para correlacionar sin
exponer contenido.

## Project Structure

```text
app/services/logger.py              -> contrato, redaccion, contexto y sinks propios
app/config.py                       -> variables APP_LOG_* y validacion
app/main.py                         -> request boundaries, health y errores seguros
app/bootstrap.py                    -> startup, servicios e ingestion
app/services/observability.py       -> adapter de TraceRecorder al logger propio
app/services/metrics.py             -> correlacion con events.jsonl sin mezclar sinks
app/services/calls.py               -> estados, turnos, VAD, resumen y excepciones
app/services/agent.py               -> RAG/modelo/fallback y resultado seguro
app/services/rag.py                 -> retrieval, revision y elegibilidad
app/services/voice.py               -> STT, limites y fallos sin guardar audio
tests/test_logger.py                -> pruebas unitarias del contrato propio
tests/test_observability_contracts.py -> redaccion, fail-open y compatibilidad
data/app.log.jsonl                  -> artefacto local ignorado por Git
```

No se agrega `data/`, logs, claves ni dumps generados al repositorio. `events.jsonl` sigue
siendo el origen de metricas de la rubrica; `app.log.jsonl` explica eventos y errores.

## Code Style

- Usar `snake_case`, tipos explicitos en los limites y funciones pequenas.
- Aceptar `Mapping[str, Any]`, normalizar a JSON seguro y no mutar el payload del llamador.
- Preferir eventos con nombres estables en `snake_case` a mensajes libres como unica
  informacion.
- Usar `contextmanager` para medir entradas/salidas y `exception()` dentro del `except`.
- Redactar antes de serializar, no despues de escribir el archivo.
- Nunca usar `print()` ni un `logging.getLogger(__name__)` como sustituto del sink propio.

Ejemplo normativo:

```python
started = time.perf_counter()
logger = logger.bind(trace_id=trace_id, call_id=call_id)
logger.log(
    LogLevel.DEBUG,
    "rag_query_started",
    message="inicia recuperacion",
    fields={"query_type": type(query).__name__, "backend": backend},
)
try:
    results = rag.search(query, limit=limit)
except Exception as exc:
    logger.exception(
        "rag_failed",
        message="la recuperacion no pudo completarse",
        error=exc,
        fields={"backend": backend},
    )
    raise
logger.log(
    LogLevel.INFO,
    "rag_query_completed",
    message="consulta RAG finalizada",
    fields={
        "hit_count": len(results),
        "corpus_revision": revision,
        "duration_ms": (time.perf_counter() - started) * 1000,
    },
)
```

El ejemplo nunca incluye `query` ni el texto de resultados. El helper `operation` debe
registrar salida normal y error exactamente una vez, con `duration_ms` y `payload_type`.

## Testing Strategy

La implementacion de la spec 24 debe consumir este contrato, pero la spec 23 necesita sus
pruebas propias antes de instrumentar todo el grafo:

1. **Unitarias:** niveles, filtro minimo, JSON estable, UTC, correlacion, redaccion de
   claves/paths, hash, rotacion y stack trace completo.
2. **Integracion:** `TestClient` con `tmp_path` comprueba que startup, `/health`, upload,
   delete, `/call`, turn, VAD, audio, RAG y error HTTP escriben eventos correlacionables.
3. **Fail-open:** un archivo no escribible o exporter remoto fallido no rompe una respuesta
   persistida; se contabiliza `observability_degraded`.
4. **Seguridad negativa:** una prueba debe fallar si aparece en el JSONL un secreto, audio,
   transcript, prompt, contenido de chunk o ruta privada.
5. **Conciliacion:** eventos de `app.log.jsonl` y metricas de `events.jsonl` comparten ids y
   permiten contrastar P50/P95 sin duplicar turnos.

## Boundaries

- **Always:** usar el logger central, validar entradas, redactar antes de persistir,
  propagar correladores, incluir stack traces en errores, conservar `events.jsonl` como
  fuente de metricas y probar el camino sin credenciales.
- **Ask first:** enviar logs fuera del equipo, cambiar la politica de PII, guardar audio o
  transcript, introducir una cola/daemon, modificar el schema SQLite o cambiar el modelo
  permitido.
- **Never:** commitear logs o secretos, registrar `.env`, volcar contexto clinico,
  confundir logs con trazas de LangSmith, dejar que el logger altere triaje/RAG, ocultar
  errores P0 por el filtro de nivel o afirmar evidencia manual desde logs sinteticos.

## Success Criteria

| ID | Criterio verificable | Evidencia |
|---|---|---|
| `LOG-AC-01` | Existe un modulo central con `DEBUG`, `INFO`, `WARN` y `ERROR` y dos sinks configurables | `tests/test_logger.py` + revision de codigo |
| `LOG-AC-02` | Cada linea local tiene schema, timestamp UTC, servicio, evento y correlador disponible | prueba JSONL |
| `LOG-AC-03` | Startup registra configuracion efectiva redacted y servicios/modelo inicializados | log de bootstrap + test |
| `LOG-AC-04` | API, admin, llamada, audio/VAD, RAG, LLM/fallback e ingestion tienen entradas/salidas o transiciones | pruebas de integracion |
| `LOG-AC-05` | Un `try/except` conserva clase y stack trace completo, pero la respuesta HTTP no expone secretos | prueba de excepcion |
| `LOG-AC-06` | El log correlaciona `call_id`, `listen_id`, `turn_id`, fuentes, revision y metricas sin transcript/audio | conciliacion JSONL |
| `LOG-AC-07` | No aparecen PII, prompts, chunks, audio, API keys ni paths privados en el archivo o consola | pruebas negativas |
| `LOG-AC-08` | Fallar el sink o LangSmith no rompe persistencia clinica y deja senal `observability_degraded` | prueba fail-open |
| `LOG-AC-09` | Los eventos de diagnostico y `events.jsonl` no duplican turnos ni alteran `/api/metrics` | regresion de metricas |
| `LOG-AC-10` | La configuracion local no descarga dependencias ni exige red y cabe en el setup de 15 minutos | comando de bootstrap |

## Implementation Plan and Tasks

1. Definir `LogLevel`, schema, redactor, contexto y sinks en `app/services/logger.py`.
2. Agregar `APP_LOG_*` a `Settings`, `.env.example` y `/health` sin exponer secretos.
3. Adaptar `TraceRecorder` y `MetricsService` sin romper sus contratos existentes.
4. Instrumentar startup, API, admin, llamadas, VAD/audio, RAG, agente, ingestion y
   excepciones con eventos de entrada/salida acotados.
5. Agregar unitarias de redaccion/stack/rotacion y pruebas de integracion con `tmp_path`.
6. Ejecutar la suite enfocada, la suite completa, `ruff`, validacion del dataset y una
   inspeccion de ausencia de secretos antes de abrir la spec de testing.

## Open Questions

1. El valor por defecto de `APP_LOG_PATH` es `data/app.log.jsonl`; si el despliegue necesita
   syslog, OpenTelemetry o un colector remoto, debe especificarse como adapter posterior.
2. La retencion local propuesta es por tamano y tres backups. Cambiarla por dias requiere
   confirmar espacio disponible y politica de evidencia.
3. La spec no decide si la auditoria de eventos de llamada se replica en SQLite; por defecto
   JSONL es diagnostico y SQLite sigue siendo autoridad de estado.
