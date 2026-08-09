# Spec: Timeout configurable de escucha del paciente

**Estado:** implementada como watchdog del baseline; cierre VAD de segmentos definido por la Spec 22
**Version:** 0.2.0
**Fecha:** 2026-08-08

## Objetivo

Implementar un limite configurable para el turno en el que el navegador escucha al paciente y
publicar ese valor en `.env.example`. El objetivo es evitar que el tiempo de escucha percibido
sea demasiado corto, sin confundirlo con los timeouts del LLM, STT o SQLite y sin convertir un
silencio en una decision clinica.

El runtime usa `SpeechRecognition` en `es-CO` con `continuous=false`,
`interimResults=true` y un timer propio por intento. El valor efectivo llega al navegador desde
`GET /health`; el navegador no lee `.env`.

### Precedencia posterior

La [`Spec 22`](22_audio_engine_continuous_vad_specification.md) es sucesora para la experiencia
de llamada continua: `VOICE_SILENCE_TIMEOUT_MS` decide el cierre técnico de un segmento solo si
existe voz y texto confirmado. Esta spec conserva `PATIENT_LISTEN_TIMEOUT_MS` como watchdog total
del reconocimiento, con consecuencias seguras y sin cuenta regresiva visible. Los contratos de
idempotencia, eventos sin texto clínico y rechazo de transcript tardío siguen vigentes.

## Tech Stack

Se conserva la Web Speech API del navegador, `SpeechRecognition`/`webkitSpeechRecognition` en
`es-CO`, `SpeechSynthesis`, FastAPI para exponer configuracion publica y la instrumentacion
JSONL existente. No se agrega un modelo de razonamiento nuevo ni se cambia la familia Llama
permitida. Whisper, Groq, SQLite, embeddings, Chroma y retrieval mantienen timeouts independientes
definidos por `RAG-ENV-001`.

## Project Structure

- `.env.example`: valor documentado `PATIENT_LISTEN_TIMEOUT_MS=30000`.
- `app/config.py`: parseo, default, rango y valor efectivo.
- `app/main.py`: `/health`, configuracion publica y eventos de escucha.
- `app/web/app.js`: maquina de estados, timer, resultados parciales y fallback textual.
- `app/services/metrics.py` y `data/events.jsonl`: eventos de observabilidad del servidor.
- `tests/`: configuracion, carreras de eventos, API e integracion de llamada.

Estas rutas contienen la implementacion de este corte. `specs/06_system_flow_diagram_specification.md`,
`README.md` raiz y `docs/` quedan para la actualizacion final de sus agentes propietarios.

## Estado de implementacion

- `Settings` aplica default `30000`, rango estricto inclusivo `1000..300000` y rechaza valores
  ausentes solo como default; vacios, no numericos y fuera de rango fallan al arrancar, tambien
  cuando se construye directamente.
- `GET /health` publica `patient_listen_timeout_ms` sin credenciales. Los timeouts de Groq,
  Whisper y SQLite conservan sus valores independientes.
- `listening_attempts` conserva por llamada el `listen_id`, `client_turn_id`, estado, timeout,
  duracion, resultado persistido e IDs de turnos; la migracion es idempotente y conserva
  `enabled` y snapshots de la spec 04.
- `POST /api/calls/{call_id}/voice-events` solo acepta los eventos acotados de esta spec y
  nunca recibe audio ni texto clinico. Los eventos se escriben en JSONL sin entrar en P50/P95
  de respuesta.
- La reclamacion de un transcript ocurre antes del agente y la restriccion unica es por
  `(call_id, client_turn_id)`. Reintentos devuelven la respuesta persistida con `duplicate=true`;
  un timeout registrado hace que un transcript posterior responda `409 late_transcript`.
- Timeout, no respuesta, parcial y error no crean turnos clinicos, alertas ni decisiones de
  triaje. La UI conserva el fallback textual y descarta callbacks tardios.

Las pruebas automatizadas de esta entrega cubren configuracion, `/health`, eventos, carreras,
idempotencia, transcript tardio, no respuesta, separacion de timeouts y ausencia de texto o
secretos en los eventos. No sustituyen el smoke manual con microfono y audio reales.

## Code Style

La maquina de estados debe aceptar eventos tardios sin efectos duplicados. Las transiciones se
expresan por estados explicitos (`LISTENING`, `PROCESSING`, `LISTEN_TIMEOUT`, `RETRY_REQUIRED`)
y el servidor usa `client_turn_id` como clave de idempotencia por llamada. No se usa un booleano
global que pueda mezclar dos llamadas o dos turnos.

## Semantica heredada del baseline

La implementacion interpreta "timeout de escucha" como **duracion maxima total de un turno de
escucha**, no como tiempo de silencio. Se configura con:

```dotenv
PATIENT_LISTEN_TIMEOUT_MS=30000
```

`30000` ms es el default vigente y puede ajustarse con la experiencia y metricas reales. La
diferencia con el limite de silencio esta resuelta en la Spec 22; no se debe reutilizar este
watchdog como la señal VAD ni mostrarlo al paciente.

### Lo que controla

- El contador inicia cuando `SpeechRecognition` emite `onstart`.
- No cuenta permisos, reproduccion de audio del agente ni la espera de red.
- El limite aplica a un turno, no a toda la llamada.
- Los resultados parciales no reinician el contador.
- Un resultado final antes del limite cancela el timer y se procesa una sola vez.
- Al alcanzar el limite, se cancela la escucha y se muestra una accion para reintentar.
- Un resultado final recibido despues del limite se descarta como tardio.
- El timeout no inicia procesamiento clinico ni invoca Groq, Whisper o el LLM por si mismo. El
  evento de observabilidad puede persistirse mediante el API y SQLite sin crear un turno clinico.

### Lo que no controla

| Operacion | Valor actual documentado | Variable independiente |
|---|---:|---|
| Groq chat | 12 s | timeout del adaptador de agente |
| Whisper STT | 30 s | timeout del servicio de voz |
| SQLite | 5 s | `busy_timeout` de base |
| Escucha paciente | 30 s por defecto | `PATIENT_LISTEN_TIMEOUT_MS` |

Cambiar la variable del paciente no puede alterar los tres valores anteriores.

## Estados y comportamiento seguro

| Estado | Comportamiento |
|---|---|
| `LISTENING` | escucha activa y contador iniciado |
| `PARTIAL` | muestra borrador, no invoca backend ni decide triaje |
| `PROCESSING` | recibio transcript final y cancelo timer |
| `NO_RESPONSE` | el navegador termino sin transcript final antes del limite |
| `LISTEN_TIMEOUT` | se alcanzo el limite configurado |
| `RECOGNITION_ERROR` | permiso, soporte, red u otro error del navegador |
| `RETRY_REQUIRED` | estado visible para repetir o usar texto |

Reglas:

1. Si el timeout ocurre sin transcript final, no se crea respuesta clinica, no se clasifica
   `verde` y no se cierra la llamada.
2. Si solo existe transcript parcial, se limpia el borrador clinico y se pide repetir; el
   parcial no se convierte automaticamente en final.
3. Si `onend` ocurre antes del limite sin texto, se registra `NO_RESPONSE`, no necesariamente
   `LISTEN_TIMEOUT`.
4. Si existe texto final antes del limite, se procesa una sola vez aunque lleguen eventos
   `onend` o parciales duplicados.
5. Un texto tardio nunca puede abrir un segundo turno.
6. Un error de permiso o navegador no se presenta como silencio del paciente.
7. Un timeout de escucha no degrada ni sobrescribe una alerta ya persistida.
8. El fallback textual permanece visible cuando la voz no esta disponible.

## Idempotencia del turno

Cada intento de escucha genera un `listen_id`. Si existe transcript final, el cliente genera
`client_turn_id` y lo envia junto con `POST /api/calls/{call_id}/turns`. El servidor debe:

- persistir una restriccion unica por `(call_id, client_turn_id)`;
- devolver la respuesta ya persistida con `duplicate=true` si recibe el mismo ID otra vez;
- devolver `409 late_transcript` si el ID llega despues de que el intento fue marcado como
  `LISTEN_TIMEOUT`;
- aceptar un resultado final exactamente en el deadline solo si su timestamp monotono es menor o
  igual al deadline; si es posterior, gana el timeout;
- no usar un ID de otra llamada ni permitir que el cliente elija un `turn_id` persistido.

Un "unico turno" en esta spec significa un unico intercambio paciente-agente identificado por
`client_turn_id`, aunque SQLite conserve filas separadas para el mensaje del paciente y la
respuesta del agente.

## Configuracion y validacion

La aplicacion debe leer la variable de entorno durante el arranque y exponer al cliente solo la
configuracion publica necesaria para el timer. Debe:

- aceptar un entero en milisegundos entre `1000` y `300000` inclusive;
- usar `30000` si la variable esta ausente;
- rechazar valores vacios, no numericos, cero, negativos o fuera del rango con error de arranque;
- no caer silenciosamente a un valor menor si la variable es invalida;
- mostrar el valor efectivo como `patient_listen_timeout_ms` en `GET /health`, sin exponer
  secretos;
- permitir que PowerShell, bash o el entorno de despliegue sobrescriban el ejemplo;
- registrar la configuracion efectiva en eventos sin incluir claves.

El valor publico debe llegar al navegador a traves de `GET /health`, no mediante lectura directa
de un archivo `.env`. Si el contrato actual de `health` no puede incluirlo, se debe actualizar ese
contrato; no se crea una segunda ruta de configuracion para esta variable.

## Flujo de voz

1. El paciente pulsa `Hablar`.
2. El navegador solicita permiso si es necesario.
3. Al iniciar reconocimiento, empieza `PATIENT_LISTEN_TIMEOUT_MS`.
4. Los parciales se muestran como borrador no clinico.
5. Un resultado final cancela el timer y envia el turno.
6. Un timeout cancela reconocimiento, registra el evento y ofrece reintento o texto.
7. El servidor solo procesa un transcript final y mantiene la politica de triaje, RAG, cita,
   respuesta y audio existente.
8. La respuesta usa `SpeechSynthesis` y la latencia obligatoria sigue midiendose desde
   `speech_ended_at` hasta `audio_started_at`; el tiempo de escucha no se mezcla con P50/P95
   de respuesta.

## Observabilidad

Registrar eventos de estado mediante el endpoint implementado
`POST /api/calls/{call_id}/voice-events`, persistidos por el servidor en
`data/events.jsonl`. Un intento de escucha tiene un `listen_id`; un transcript final tambien
lleva `client_turn_id`. El servidor debe hacer idempotente `client_turn_id` por llamada para que
un `onresult` duplicado, una carrera con `onend` o un reintento de red no creen dos intercambios.
Cada evento incluye `call_id`, `listen_id`, `client_turn_id` cuando exista,
`configured_timeout_ms`, `elapsed_ms`, locale, implementacion (`SpeechRecognition` o
`webkitSpeechRecognition`), estado del resultado y codigo de error cuando aplique:

```text
patient_listen_started
partial
final
ended
no_response
timeout
error
retry
```

No registrar audio ni texto clinico completo en estos eventos. `data/events.jsonl` es la fuente
de verdad de estos eventos; SQLite solo conserva la relacion necesaria con llamada/turno y no se
usa como segunda copia de la carga completa. Las metricas utiles son tasa de
timeout, tasa de no respuesta, duracion P50/P95 de escucha, errores por navegador y eventos
tardios descartados. La latencia conversacional sigue usando los campos existentes de voz.

## Compatibilidad browser

- Detectar `window.SpeechRecognition` y `window.webkitSpeechRecognition`.
- Conservar `lang='es-CO'` y `continuous=false` en el primer corte.
- Usar `interimResults=true`; si un navegador no entrega parciales, el flujo sigue funcionando
  sin ese estado.
- Tolerar `onend`, `onerror` y `onresult` tardios o duplicados.
- Requerir `localhost` o contexto seguro para el microfono.
- Mantener entrada textual cuando el navegador no soporte reconocimiento o niegue permiso.
- No tratar Firefox u otro navegador incompatible como un timeout del paciente.
- El timer debe usar reloj monotono del navegador y cancelarse en toda salida normal.

## Comandos de verificacion ejecutados

Durante esta implementacion se ejecutaron desde la raiz:

```text
python -m pytest tests/test_timeout.py -q
python -m pytest tests/test_api.py tests/test_calls.py tests/test_metrics.py -q
python -m pytest tests/test_admin_lifecycle.py tests/test_live_knowledge.py -q
python -m pytest -q
ruff check app tests
node --check app/web/app.js
git diff --check
```

Resultado de esta entrega: `17` pruebas enfocadas, `13` de regresion de API/llamadas/metricas,
`8` de admin/conocimiento vivo y `62` en la suite completa pasaron. La evidencia manual sigue
pendiente: Chrome o Edge, microfono real, respuesta antes del limite, silencio, parcial,
reintento, fallback textual, permiso denegado y audio del agente.

## Estrategia de pruebas

- Parsing: valor por defecto, override, ausencia, texto invalido, cero, negativo, `999` y
  `300001` rechazados, `1000` y `300000` aceptados.
- Timer: inicia en `onstart`, no durante permisos ni TTS, y se cancela con transcript final.
- Parciales: no invocan backend, no reinician timer y se limpian al vencer.
- Carreras: timer contra `onresult`, `onend` y `onerror` no genera doble turno.
- Seguridad: timeout sin texto no produce `verde`, recomendacion ni cierre automatico.
- Separacion: cambiar el timeout del paciente no cambia Groq, Whisper ni SQLite.
- Observabilidad: eventos contienen identificadores y no contienen secretos ni audio.
- Manual: Chrome/Edge con habla real, silencio, reintento, fallback textual y respuesta de
  agente; los resultados se registran como evidencia, no se infieren de mocks.

## Limites

- **Siempre:** mantener un unico intercambio por `client_turn_id`, ofrecer reintento o texto,
  preservar triaje persistido,
  medir por separado escucha y respuesta, y dejar visible el estado del microfono.
- **Preguntar antes:** definir si el timeout es total o de silencio, cambiar el idioma,
  habilitar streaming full-duplex, incorporar grabacion persistente o alterar la politica de
  reintentos.
- **Nunca:** enviar transcript parcial como instruccion clinica sin marcarlo, convertir timeout
  en `verde`, cerrar una llamada por silencio sin consentimiento, reintentar infinitamente,
  modificar timeouts de proveedores por accidente o incluir secretos en `.env.example`.

## Criterios de exito

- **TIME-AC-01:** `.env.example` contiene `PATIENT_LISTEN_TIMEOUT_MS=30000` y explica que es
  configurable y distinto de Groq, Whisper y SQLite.
- **TIME-AC-02:** el runtime usa `30000` cuando falta la variable, rechaza valores fuera de
  `1000..300000` y expone `patient_listen_timeout_ms` sin secretos.
- **TIME-AC-03:** el timer inicia con la escucha y un `client_turn_id` final genera un solo
  intercambio aunque existan eventos duplicados.
- **TIME-AC-04:** al vencer sin transcript final se detiene la escucha, se registra el evento y
  se ofrece reintento o texto sin respuesta clinica automatica.
- **TIME-AC-05:** un resultado tardio o un reintento de red no genera un segundo intercambio.
- **TIME-AC-06:** el cambio no altera los timeouts de LLM, STT ni SQLite.
- **TIME-AC-07:** la latencia P50/P95 conserva su definicion oficial y no incluye por error el
  tiempo de espera del paciente.
- **TIME-AC-08:** existe evidencia manual en navegador compatible y se documentan sus limites.

## Dependencias y preguntas abiertas

- Depende de `specs/03_mvp_structure_specification.md` para la ubicacion de `.env.example` y
  entregables.
- El agente propietario debe actualizar `specs/06_system_flow_diagram_specification.md` al final
  para reflejar el contrato implementado. README, setup, informe y evidencia publicada quedan
  fuera del alcance de este agente.
- No cambia el modelo permitido ni la politica de seguridad RAG. La migracion puede agregar
  `EMBEDDING_TIMEOUT_MS`, `VECTOR_QUERY_TIMEOUT_MS` y `RAG_QUERY_TIMEOUT_MS`, pero ninguno inicia
  un turno clinico despues de un timeout de escucha ni modifica `PATIENT_LISTEN_TIMEOUT_MS`.

Preguntas abiertas:

1. El limite total del turno queda implementado; sigue abierta si una futura iteracion necesita
   ademas un limite de silencio separado (`PATIENT_SILENCE_TIMEOUT_MS`).
2. El default vigente es 30 s y el rango `1..300` s; queda abierta su calibracion con evidencia
   manual y metricas reales.
3. Confirmar si el mismo timeout aplicara a una futura captura de audio para Whisper.
