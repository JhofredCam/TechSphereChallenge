# 2026-08-09 | Verificacion end-to-end local

## Alcance

Se verifico el checkout local con la configuracion de `.env`, sin modificar codigo de la
aplicacion ni exponer secretos. La prueba cubrio bootstrap, suite automatizada, servidor Uvicorn,
API de administracion, RAG vivo, llamadas, eventos de voz, metricas y rutas frontend.

## Comandos y resultados

- Carga temporal de las variables de `.env` para la verificacion; el servidor se inicio con
  `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env`.
- `python -m scripts.validate_dataset`: dataset valido; 3991 turnos, 40 perfiles clinicos,
  40 perfiles demograficos y 160 trayectorias.
- `python -m app.bootstrap --json`: 104 documentos unicos; 103 `available` y 1 `needs_ocr`.
  Una segunda ejecucion idempotente repuso un registro temporalmente ausente y dejo el corpus en
  104 documentos y revision 124.
- `python -m pytest -q --basetemp C:\\temp\\techsphere-pytest-run`: 157 pruebas pasadas.
  La ejecucion sin `--basetemp` encontro un bloqueo de permisos en el temporal predeterminado de
  Windows; no fue un fallo de la aplicacion.
- `GET /health`: `ok`, FTS5, 104 documentos, revision 124, timeout de escucha de 30000 ms y
  modelo declarado `llama-3.1-8b-instant`.
- Flujo HTTP vivo: upload, preview, disable, enable, pregunta fundamentada con cita, abstencion
  mientras el documento estaba deshabilitado, recuperacion al habilitar, delete, olvido sin
  reiniciar, cierre de llamada, evento `patient_listen_started` y `/api/metrics`: todo paso.
- El adaptador remoto Groq fue invocado en una pregunta fundamentada (`provider=groq`, una
  invocacion). La salida sin cita valida se rechazo y se uso el fallback extractivo seguro.
- Rutas `/`, `/patient`, `/admin/access`, `/admin`, `/call` y `/docs`: HTTP 200. Todos los JS de
  `app/web/` pasaron `node --check`.

## Pendientes y riesgos

- El conector del navegador integrado no pudo inicializarse en esta sesion por
  `Cannot redefine property: process`; por eso quedan pendientes la inspeccion visual manual,
  permiso real de microfono y reproduccion de audio del navegador.
- No se envio audio real a Whisper porque no hay un archivo de voz local en el repositorio; el
  modo expuesto por `/health` es `groq-whisper` y la ruta browser/API esta cubierta por contratos
  automatizados.

## Siguiente accion verificable

Abrir `http://127.0.0.1:8000/admin` y `http://127.0.0.1:8000/call` en Chrome o Edge, permitir el
microfono y completar un turno real para cerrar la evidencia manual de voz.
