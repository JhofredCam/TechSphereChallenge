# 2026-08-09 | Prevencion de 409 por timeout de voz

## Alcance

Se investigaron dos respuestas `409 Conflict` aparecidas al finalizar el tercer intento de una
llamada continua: una en `/voice-events` y otra en `/turns`. La correccion se especifico en
[`CALL-VOICE-026`](../../specs/26_voice_timeout_final_race_specification.md) y se implemento en
la rama `spec/voice-timeout-final-race`.

## Hallazgo y decision

El intento supero el timeout total de 30000 ms. El callback final de SpeechRecognition envio en
paralelo el evento `final` y el transcript; el backend marco `LISTEN_TIMEOUT`, no creo turnos y
rechazo ambos requests como `late_transcript`.

La causa que hacia que un tercer turno llegara tarde de forma artificial estaba en el cliente
continuo: `callState.currentAttempt` se reutilizaba aunque el `listenId` ya habia cambiado, por lo
que el nuevo intento heredaba el `startedAt` del anterior. Ahora cada `listenId` nuevo crea un
intento independiente. Si el callback final sigue llegando tarde, el cliente registra solo
`timeout`, muestra reintento y no llama `/turns`. El backend conserva su rechazo seguro para
clientes externos tardios.

## Archivos y verificacion

- `app/web/app.js`: nuevos intentos por `listenId` y guarda de timeout antes de `final`/`sendTurn`.
- `tests/test_call_ui_contracts.py`: contrato estatico de la guarda y refresco del intento.
- `specs/26_voice_timeout_final_race_specification.md`, `tasks/` y esta bitacora: alcance y
  evidencia reproducible.

Comandos ejecutados:

```text
python -m pytest tests/test_call_ui_contracts.py tests/test_voice_events.py tests/test_timeout.py -q --basetemp .pytest-tmp/voice-timeout-focused
node --check app/web/app.js
node --check app/web/voice-loop.js
python -m pytest -q --basetemp .pytest-tmp/voice-timeout-race-full
ruff check app tests
git diff --check
```

La suite enfocada paso 22 pruebas. El smoke real con Chrome/Edge y microfono queda pendiente;
la prueba debe cubrir un resultado dentro del limite y otro posterior al limite.

## Riesgos y siguiente accion

Los `409` del caso ya persistido son historicos y no se reintentan: ese intento queda en
`LISTEN_TIMEOUT` sin turnos. Reinicia Uvicorn, abre una llamada nueva y prueba al menos tres
turnos consecutivos para verificar que cada uno inicia su propio reloj.
