# 2026-08-09 | Invalidacion de assets frontend de voz

## Alcance

Se reviso un nuevo par de `409 Conflict` despues de la correccion de timeout continuo. Los
eventos mostraron otra vez tiempos acumulados entre turnos aunque cada intento de voz duraba
pocos segundos, señal de que el navegador seguia ejecutando el `app.js` anterior.

## Hallazgo y decision

Las respuestas de `/call` y `/static/*.js` no tenian `Cache-Control`; el navegador podia conservar
la version previa y no recibir la guarda por `listenId` ni el timeout tardio. Se agrego un handler
estatico sin cache, headers `no-store` para las paginas y versionado de los assets de llamada y
admin. El backend no cambia su contrato: un cliente realmente tardio sigue recibiendo
`409 late_transcript`.

## Archivos y verificacion

- `app/main.py`: headers no-cache para paginas y assets estaticos.
- `app/web/call.html`, `app/web/admin.html`: query versionada para scripts actualizados.
- `tests/test_frontend_routes.py`: regresion de headers y referencias versionadas.

Comandos ejecutados:

```text
python -m pytest tests/test_frontend_routes.py tests/test_call_ui_contracts.py tests/test_timeout.py -q --basetemp .pytest-tmp/asset-cache-focused
python -m pytest -q --basetemp .pytest-tmp/asset-cache-full
ruff check app tests
node --check app/web/app.js
node --check app/web/voice-loop.js
git diff --check
```

## Riesgos y siguiente accion

El navegador que ya tiene una pagina abierta debe recargar `/call`; las siguientes cargas reciben
los scripts versionados sin cache. La prueba manual pendiente es realizar tres turnos nuevos en
Chrome/Edge y comprobar que cada `vad_speech_started` tiene su propio `elapsed_ms` cercano a cero.
