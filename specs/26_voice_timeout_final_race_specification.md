# Spec: Prevencion de 409 por transcript tardio en voz continua

**ID:** `CALL-VOICE-026`
**Estado:** `IMPLEMENTED`
**Fecha:** 2026-08-09
**Depende de:** [`specs/22_audio_vad_specification.md`](22_audio_vad_specification.md),
[`specs/25_agent_response_recovery_specification.md`](25_agent_response_recovery_specification.md)

## Supuestos y diagnostico

1. El `409` observado pertenece a un intento de escucha continuo que supero el timeout total
   configurado de 30000 ms; no es un rechazo clinico del agente ni un problema de Groq.
2. El navegador puede entregar el callback final de SpeechRecognition despues del timeout del
   intento y, en ese momento, enviar en paralelo el evento `final` y `POST /turns`.
3. El backend debe conservar el contrato de seguridad actual: un transcript tardio no crea un
   turno clinico y los clientes externos siguen recibiendo `409 late_transcript`.
4. El cambio se limita al cliente de voz continua; no se agrega una dependencia ni se amplia el
   timeout para aceptar resultados fuera de plazo.

## Objetivo

Evitar que la interfaz browser/API genere dos requests `409` cuando el resultado de voz llega
despues del limite. Para un resultado tardio, la interfaz debe registrar un unico `timeout`,
mostrar el estado de reintento y no llamar a `/turns`. Para un resultado dentro del limite, debe
conservar el flujo actual `final` + `/turns` y la respuesta del agente.

## Tech Stack

- JavaScript vanilla en `app/web/voice-loop.js` y `app/web/app.js`.
- FastAPI/SQLite para el contrato de eventos y turnos existente.
- Jest no esta instalado; los contratos frontend se verifican con pytest estatico y `node --check`.

## Commands

```text
python -m pytest tests/test_call_ui_contracts.py tests/test_voice_events.py tests/test_timeout.py -q --basetemp .pytest-tmp/voice-timeout-race
python -m pytest -q --basetemp .pytest-tmp/voice-timeout-race-full
node --check app/web/app.js
node --check app/web/voice-loop.js
ruff check app tests
git diff --check
```

## Project Structure

```text
app/web/voice-loop.js       -> deteccion de silencio y finalizacion continua.
app/web/app.js              -> envio de eventos, turnos y estados visibles.
app/services/calls.py       -> autoridad del timeout y rechazo seguro de tardios.
tests/test_call_ui_contracts.py -> contrato estatico de la proteccion frontend.
tests/test_voice_events.py, tests/test_timeout.py -> regresiones HTTP/servicio.
tasks/plan.md, tasks/todo.md -> plan y tareas de esta correccion.
readme/06_bitacora_de_sesiones/ -> evidencia de la sesion.
```

## Code Style

La guarda debe decidir antes de emitir `final` o enviar el turno y reutilizar el estado terminal
de timeout:

```javascript
const elapsed = attempt.startedAt ? monotonicNow() - attempt.startedAt : 0;
if (elapsed > callState.patientListenTimeoutMs) {
  markAttemptTimeout(attempt, elapsed);
  return;
}
registerVoiceEvent(attempt, "final", { elapsed_ms: elapsed });
void sendTurn(text, timing, attempt);
```

Se conservan nombres `camelCase` en JavaScript, estados en mayusculas, una sola transicion
terminal por intento y mensajes patient-facing del catalogo existente. La logica de seguridad
del backend no se duplica ni se debilita en el navegador.

## Testing Strategy

- Contrato estatico: verificar que el callback continuo comprueba el timeout, emite `timeout` y
  retorna antes de registrar `final` o invocar `sendTurn`.
- Regresion backend: conservar las pruebas que garantizan `409 late_transcript` para clientes que
  intentan enviar tarde y que un timeout no crea turnos.
- Regresion frontend: `node --check` sobre ambos archivos y suite completa para asegurar que el
  flujo dentro de plazo continua funcionando.
- Smoke manual pendiente: Chrome/Edge con microfono real, un resultado antes del limite y otro
  que llegue despues del limite.

## Boundaries

- **Always:** respetar el timeout de `/health`, registrar telemetria sin texto clinico, emitir un
  solo evento terminal, conservar reintento visible y probar antes del commit.
- **Ask first:** cambiar la duracion del timeout, aceptar transcripts tardios en el backend,
  modificar el esquema SQLite, agregar una dependencia frontend o alterar el catalogo de copy.
- **Never:** enviar un transcript tardio a `/turns`, crear un turno despues de `LISTEN_TIMEOUT`,
  ocultar un error clinico, eliminar la proteccion backend o commitear datos de `data/`.

## Success Criteria

- **`CALL-VOICE-AC-01`:** un resultado continuo con `elapsed_ms > patient_listen_timeout_ms`
  marca el intento `LISTEN_TIMEOUT`, registra `timeout` una vez y no ejecuta `sendTurn`.
- **`CALL-VOICE-AC-02`:** la interfaz no produce `POST /voice-events` de tipo `final` para ese
  resultado tardio y no aparecen dos conflictos consecutivos.
- **`CALL-VOICE-AC-03`:** un resultado dentro del limite conserva `final` + `/turns`, recibe
  respuesta del agente y no cambia el contrato de fuentes, triaje o audio.
- **`CALL-VOICE-AC-04`:** el backend sigue rechazando un transcript tardio externo con
  `409 late_transcript` y no persiste turnos.
- **`CALL-VOICE-AC-05`:** pruebas enfocadas, suite completa, Ruff, Node y diff check pasan.

## Open Questions

1. El smoke de navegador real sigue pendiente; esta correccion evita la carrera conocida, pero no
   sustituye probar SpeechRecognition en Chrome/Edge.
