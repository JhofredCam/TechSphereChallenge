# Spec: Motor de audio para conversación continua y VAD

**ID:** `AUDIO-VAD-022`
**Estado:** `IMPLEMENTED`; ciclo VAD continuo, eventos y estados integrados; prueba de micrófono/audio pendiente
**Versión:** 0.1.0
**Fecha:** 2026-08-09
**Propietario:** captura de voz, detección de silencio e integración browser/API
**Depende de:** [`05_patient_listening_timeout_specification.md`](05_patient_listening_timeout_specification.md), [`06_system_flow_diagram_specification.md`](06_system_flow_diagram_specification.md), [`07_testing_unit_integration_specification.md`](07_testing_unit_integration_specification.md), [`11_conversational_ux_writing_specification.md`](11_conversational_ux_writing_specification.md)
**Coordina con:** [`20_frontend_architecture_routing_demo_state_specification.md`](20_frontend_architecture_routing_demo_state_specification.md) y [`21_patient_portal_call_ux_specification.md`](21_patient_portal_call_ux_specification.md)

## Objective

Reemplazar el patrón de “pulsar Hablar por cada mensaje” por una llamada browser/API con ciclos
automáticos de escucha, procesamiento y respuesta. El paciente habla con manos libres; el sistema
detecta que dejó de hablar, cierra solo ese segmento y continúa escuchando después del audio del
agente.

### Decisión de precedencia

Esta spec introduce el cierre automático por silencio solicitado para la nueva llamada continua.
Por tanto, reemplaza en la Spec 05 la regla de que el silencio nunca finaliza un segmento y ajusta
la Spec 11: no hay cuenta regresiva ni presión visible, pero sí una decisión técnica de segmento
cuando existe voz y el silencio estable supera `VOICE_SILENCE_TIMEOUT_MS`.

`PATIENT_LISTEN_TIMEOUT_MS` permanece como watchdog técnico del navegador/servidor para impedir un
reconocimiento colgado. No se muestra como tiempo restante, no clasifica triaje y no crea turnos.
La continuidad se refiere a la experiencia entre segmentos, no a mantener un único transcript
infinito.

### Supuestos explícitos

1. El primer corte usa Web Audio API para nivel de señal y `SpeechRecognition`/`webkitSpeechRecognition`
   para texto en `es-CO`; no guarda audio.
2. La captura `getUserMedia` y el reconocimiento se coordinan en un controlador de ciclo; el
   permiso se solicita una sola vez por llamada siempre que el navegador lo permita.
3. `SpeechSynthesis` sigue siendo TTS del agente. El controlador no reinicia micrófono mientras
   el agente está hablando, salvo que una implementación futura demuestre barge-in seguro.
4. Un segmento sin texto confirmado nunca se envía a `POST /turns` ni modifica triaje.
5. Los valores de `.env.example` llegan al navegador por configuración pública de `/health` o un
   endpoint de configuración sin secretos; el JS no intenta leer `.env`.

## Tech Stack

- Web Audio API: `MediaStream`, `AudioContext`, `AnalyserNode` y cálculo RMS.
- Web Speech API: `SpeechRecognition` o `webkitSpeechRecognition`, `lang = "es-CO"`.
- `SpeechSynthesis` para audio de respuesta.
- JavaScript ES2022, `requestAnimationFrame` o intervalos cortos cancelables, `AbortController`
  para requests y `performance.now()` para tiempos monotónicos.
- API existente: `POST /api/calls/{id}/voice-events`, `POST /api/calls/{id}/turns`,
  `POST /api/calls/{id}/turns/{turn_id}/voice-timing` y `GET /health`.
- Configuración objetivo en `.env.example`:

```text
VOICE_SILENCE_TIMEOUT_MS=2000
VOICE_VAD_RMS_THRESHOLD=0.025
VOICE_SPEECH_START_TIMEOUT_MS=10000
PATIENT_LISTEN_TIMEOUT_MS=30000
```

`VOICE_SILENCE_TIMEOUT_MS` debe validarse entre 500 y 10000 ms; `VOICE_VAD_RMS_THRESHOLD` entre
0.001 y 0.2; `VOICE_SPEECH_START_TIMEOUT_MS` entre 1000 y 30000 ms. Los límites protegen contra
una UX que corta demasiado pronto o que deja el micrófono abierto indefinidamente.

## Commands

```text
python -m pytest tests/test_timeout.py tests/test_voice.py tests/test_calls.py -q
python -m pytest tests/test_vad.py tests/test_voice_events.py -q
python -m pytest tests/test_api.py tests/test_metrics.py -q
node --check app/web/app.js
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
git diff --check
```

`tests/test_vad.py` y `tests/test_voice_events.py` son archivos objetivo; no se debe sustituir
la prueba manual por mocks para declarar G4.

## Project Structure

```text
app/config.py                    -> defaults y validación de VAD/watchdog
app/main.py                      -> expone configuración pública y nuevos event types
app/schemas.py                   -> contratos persistibles sin audio ni transcript parcial
app/services/calls.py            -> idempotencia, turnos y eventos de segmento
app/web/voice-loop.js            -> controlador continuo, VAD y máquina de estados
app/web/app.js                   -> integración del controlador con /call
app/web/call.html                -> estados accesibles y acción de terminar escucha
app/web/messages.js              -> copy de escucha, procesamiento, respuesta y errores
tests/test_vad.py                -> algoritmo determinista con muestras sintéticas
tests/test_voice_events.py       -> contrato HTTP, orden e idempotencia
tests/test_timeout.py            -> watchdog heredado y no creación de turnos tardíos
```

## State Machine and Event Contract

### Estados de producto

| Estado | Texto UI | Entrada | Salida |
|---|---|---|---|
| `IDLE` | `Listo para escucharte` | iniciar llamada | `LISTENING` |
| `LISTENING` | `Escuchando` | permiso + reconocimiento | voz, silencio, error o cierre |
| `PROCESSING` | `Procesando` | silencio estable con transcript | turno enviado |
| `RESPONDING` | `Respondiendo` | respuesta + TTS | audio terminado |
| `RECONNECTING` | `Preparando la escucha` | TTS terminado | `LISTENING` |
| `ENDED` | `Atención cerrada` | cierre explícito | resumen |
| `ERROR` | `No pude escucharte bien` | permiso/API/red | reintento o texto |

`PROCESSING` y `RESPONDING` son estados mutuamente exclusivos de `LISTENING`. El triaje se
actualiza únicamente después de un turno aceptado y responde a las reglas deterministas
existentes.

### Eventos observables

Los eventos se envían a `/voice-events`, son idempotentes por `call_id + listen_id + sequence` y
no contienen audio ni texto clínico completo:

```text
patient_listen_started
vad_speech_started
vad_silence_started
vad_segment_finalized
partial
final
ended
no_response
timeout
error
retry
```

Cada evento puede incluir `listen_id`, `client_turn_id` cuando exista, `sequence`, `elapsed_ms`,
`configured_timeout_ms`, `silence_timeout_ms`, `locale`, `implementation` y `error_code`.
`final` exige `client_turn_id`; `vad_silence_started` nunca crea un turno. Si el backend aún no
acepta los nuevos tipos, el cambio debe versionar el contrato y rechazar eventos desconocidos de
forma explícita, nunca fingir persistencia.

## VAD Algorithm

El VAD no intenta entender la semántica clínica. Solo decide cuándo terminó un segmento de voz.
El reconocimiento de texto y la decisión clínica siguen separados.

```text
startCall()
  loadPublicVoiceConfig()
  request microphone once
  state = LISTENING
  recognition.start({ lang: "es-CO", continuous: true, interimResults: true })

onAudioFrame(rms):
  level = smooth(rms, window=5 frames)
  speaking = level >= calibratedThreshold
  if speaking and !hasSpeech:
    hasSpeech = true
    silenceSince = null
    emit vad_speech_started
  if hasSpeech and !speaking and silenceSince == null:
    silenceSince = now()
    emit vad_silence_started
  if hasSpeech and silenceSince != null:
    if now() - silenceSince >= VOICE_SILENCE_TIMEOUT_MS
       and transcriptBuffer.confirmedText is not empty:
      stopRecognition()
      state = PROCESSING
      emit vad_segment_finalized
      submit exactly once with client_turn_id + listen_id
    if speaking:
      silenceSince = null

onRecognitionResult(result):
  append final text to confirmedText
  keep interim text as draft only
  render draft without sending clinical request

onResponseAudioEnded():
  clear segment state
  if call is active: state = LISTENING; recognition.start()

onNoTextAtSilence():
  keep state LISTENING; clear draft; emit no_response only after explicit end/watchdog
```

### Guardas contra ruido y carreras

- calibrar el nivel ambiente durante los primeros 300 ms sin cortar por ese período;
- suavizar RMS y exigir cinco frames coherentes antes de cambiar `speaking`;
- aplicar histéresis: el umbral de salida puede ser 80% del de entrada;
- no finalizar si `confirmedText` está vacío, aunque el micrófono lleve silencio;
- si llega `onresult` durante la ventana de silencio, reiniciar el contador y conservar texto;
- cancelar `requestAnimationFrame`, tracks, `AudioContext`, timers y listeners en toda salida;
- proteger el submit con `finalizedListenIds` y hacer que el servidor mantenga la idempotencia de
  `client_turn_id` existente;
- no reiniciar escucha hasta que TTS termine y no exista un cierre pendiente;
- si SpeechRecognition termina por error, mostrar fallback textual y permitir `Reintentar`.

## Code Style

La lógica VAD debe ser pura respecto de muestras para poder probarla sin micrófono:

```js
export function nextVadState(previous, sample, config, nowMs) {
  const speaking = sample.rms >= config.rmsThreshold;
  const silenceStartedAt = speaking ? null : (previous.silenceStartedAt ?? nowMs);
  const silenceMs = silenceStartedAt === null ? 0 : nowMs - silenceStartedAt;
  const shouldFinalize = previous.hasSpeech
    && silenceMs >= config.silenceTimeoutMs
    && previous.confirmedText.trim().length > 0;

  return {
    hasSpeech: previous.hasSpeech || speaking,
    silenceStartedAt,
    phase: shouldFinalize ? "PROCESSING" : "LISTENING",
    shouldFinalize,
  };
}
```

Usar nombres en `camelCase`, tipos explícitos en los límites, errores seguros del catálogo de
mensajes y `textContent` para todo texto. Nunca enviar parciales como `text` al endpoint clínico.

## Testing Strategy

### Unitarias deterministas

- default 2000 ms y overrides válidos/invalidos en `Settings.from_env`;
- nivel debajo/encima del umbral, ruido breve, pausa menor al umbral y silencio estable mayor al
  umbral;
- texto vacío no finaliza; texto confirmado sí finaliza una única vez;
- histéresis, calibración y frames tardíos no producen una doble finalización;
- al cambiar a `PROCESSING`, se cancelan captura y timers de escucha;
- al terminar TTS, el ciclo vuelve a `LISTENING` sin crear llamada nueva.

### Integración HTTP

- `GET /health` expone defaults públicos sin claves;
- eventos VAD válidos se persisten sin audio ni texto clínico;
- evento duplicado o `client_turn_id` repetido no crea dos turnos;
- silencio sin transcript no llama al agente ni cambia triaje;
- timeout técnico total conserva el comportamiento seguro de la Spec 05;
- un error de proveedor o permiso ofrece texto/reintento y no se presenta como respuesta clínica.

### Smoke manual de voz

En Chrome o Edge, con contexto `127.0.0.1`/localhost:

1. iniciar llamada y conceder micrófono;
2. decir un saludo, permanecer en silencio aproximadamente 2 s y observar `Procesando`;
3. comprobar que el agente responde con audio y que vuelve a `Escuchando`;
4. hablar dos segmentos seguidos sin pulsar el botón por cada turno;
5. probar una pausa corta, ruido de fondo, permiso denegado, navegador incompatible y fallback
   textual;
6. confirmar que la transcripción final, fuentes, triaje, timing y cierre permanecen auditables.

Registrar tiempos reales y navegador. El mock del analizador valida algoritmo, no G4.

## Observability and Metrics

Conservar las métricas existentes de respuesta desde `speech_ended_at` hasta `audio_started_at`.
Agregar, sin texto clínico completo:

- duración de segmento P50/P95;
- tiempo silencio→submit P50/P95;
- tasa de segmentos vacíos, dobles y descartados;
- tasa de errores por navegador y permiso;
- tasa de retorno `RESPONDING → LISTENING`;
- valor efectivo de `VOICE_SILENCE_TIMEOUT_MS` y umbral RMS.

Los logs deben redactar identificadores de paciente cuando no sean necesarios, no guardar audio y
no incluir secretos. El README final debe separar estas métricas de latencia de respuesta y costo
obligatorias de la rúbrica.

## Boundaries

- **Always:** mantener `es-CO`, una sola solicitud por segmento, idempotencia, fallback textual,
  triaje determinista, no enviar parciales, cancelar recursos, separar VAD de STT/TTS y registrar
  estados sin contenido clínico.
- **Ask first:** cambiar el default o rango de silencio, habilitar barge-in, grabar audio,
  incorporar WebRTC/full-duplex, usar un VAD remoto, modificar la política de reintentos o cambiar
  el modelo permitido.
- **Never:** finalizar un segmento vacío como turno clínico, convertir silencio en verde, usar el
  umbral de VAD para decidir urgencia, leer `.env` desde el navegador, exponer secretos, reintentar
  infinitamente o afirmar G4 con una prueba simulada.

## Success Criteria

| ID | Criterio verificable | Evidencia |
|---|---|---|
| `VAD-AC-01` | una llamada encadena escucha, procesamiento y respuesta sin pulsar por turno | smoke Chrome/Edge |
| `VAD-AC-02` | `VOICE_SILENCE_TIMEOUT_MS=2000` es default, configurable y validado | config + unitarias |
| `VAD-AC-03` | el silencio solo finaliza si existe voz/transcript confirmado | `test_vad.py` |
| `VAD-AC-04` | una carrera entre VAD, `onresult` y `onend` produce un solo turno | integración |
| `VAD-AC-05` | UI muestra exactamente `Escuchando`, `Procesando`, `Respondiendo` | contrato UI |
| `VAD-AC-06` | no se guarda audio ni transcript parcial en eventos | pruebas de red/log |
| `VAD-AC-07` | timeout técnico total permanece separado y seguro | regresión Spec 05 |
| `VAD-AC-08` | TTS termina antes de reactivar escucha y no se escucha a sí mismo | smoke manual |
| `VAD-AC-09` | latencia y segmentos reportan métricas reales, no valores inventados | `/api/metrics` + bitácora |
| `VAD-AC-10` | G4 se prueba con micrófono y audio reales, no con mocks | evidencia manual |

## Implementation Plan and Tasks

1. Extender settings y `.env.example` con variables VAD, límites y configuración pública.
2. Versionar los nuevos eventos y conservar compatibilidad/idempotencia de la Spec 05.
3. Implementar `voice-loop.js` con RMS, histéresis, temporizadores y cleanup.
4. Integrar la máquina de estados con `/call`, mensajes y rail de la Spec 21.
5. Añadir pruebas puras, HTTP, carreras y regresiones de timeout/llamadas.
6. Ejecutar smoke manual y actualizar la vista normativa de Spec 06, README, informe y bitácora.

## Open Questions

1. ¿Se mantiene SpeechRecognition como STT principal o se debe usar `MediaRecorder` por segmento y
   Whisper? Se recomienda mantener Web Speech para el primer corte por latencia y arranque en 15
   minutos; Whisper queda como fallback/API.
2. ¿El umbral RMS requiere calibración por dispositivo? Sí para una versión robusta; el primer
   corte debe usar calibración corta y un override documentado.
3. ¿Se permite barge-in mientras habla el agente? No en este alcance: requiere separar audio de
   salida y entrada y probar que no duplica turnos.
