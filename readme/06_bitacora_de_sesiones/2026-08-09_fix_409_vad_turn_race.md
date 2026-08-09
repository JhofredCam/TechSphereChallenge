# 2026-08-09 | Correccion del 409 entre VAD y turnos

## Alcance

Se investigó el `409 Conflict` observado en `POST /api/calls/{id}/turns` durante una llamada
continua. Se corrigió la carrera entre el evento `vad_segment_finalized` y el envío del
transcript clínico.

## Hallazgo y decisión

El evento `vad_segment_finalized` llegaba primero y creaba el intento con estado `PROCESSING`.
Cuando llegaba el `POST /turns` con el mismo `client_turn_id`, el servidor lo interpretaba como
otro turno todavía en curso y devolvía `409 turn_in_progress`. El evento VAD no contiene el
transcript clínico y solo debe registrar telemetría; ahora conserva el intento en estado activo y
`POST /turns` es quien reclama el procesamiento.

## Archivos y verificación

- `app/services/calls.py`: el evento VAD ya no reclama el intento.
- `tests/test_voice_events.py`: regresión HTTP con el orden VAD -> turno.

Comandos ejecutados:

```text
python -m pytest tests/test_voice_events.py tests/test_timeout.py -q
node --check app/web/app.js
git diff --check
```

## Riesgos y siguiente acción

La corrección cubre la carrera de persistencia que produjo el `409`; queda pendiente repetir el
smoke con micrófono real en Chrome/Edge para verificar el ciclo completo de VAD, TTS y reanudación.
