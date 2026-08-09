# 06 - Deployment

## Objetivo

Dejar el MVP levantable localmente y demostrable desde un navegador, con una ruta operativa
que el jurado pueda seguir en 15 minutos o menos. Deployment aqui significa ejecucion local
reproducible, no telefonia ni despliegue hospitalario.

## Entradas

- [Setup local](../../../readme/02_setup_local.md).
- [Guion de demo](../../../readme/03_demo_funcional.md).
- Componentes de aplicacion definidos en la [especificacion](../../../specs/00_mvp_specification.md#estructura-del-proyecto).
- Evidencia y criterios de [Evaluation](../05_evaluation/README.md).
- [Diagrama de arquitectura](../../../docs/arquitectura.md).
- [Diagrama normativo del siguiente corte](../../../specs/06_system_flow_diagram_specification.md).
- [Timeout configurable de escucha](../../../specs/05_patient_listening_timeout_specification.md).

## Salidas

- Entorno Python reproducible con dependencias declaradas en `requirements.txt`.
- Bootstrap local que crea base, valida dataset y procesa el corpus sin descargar datos.
- Servidor FastAPI/Uvicorn accesible en `127.0.0.1:8000`.
- `/admin` para upload, listado, preview textual, estado `available`/`needs_ocr`,
  enable/disable y delete.
- `/call` para llamada browser/API con microfono, transcripcion, timeout total por turno,
  respuesta, audio y fallback textual.
- Instrucciones de permisos, fallback textual, variables de entorno y limpieza segura.
- `PATIENT_LISTEN_TIMEOUT_MS=30000` se valida en `app.config`, llega por `/health` y controla
  cada intento de escucha; es independiente de Groq, Whisper y SQLite.
- Registro del tiempo real de setup y resultado de cada recorrido de demo.

## Tareas concretas

1. Declarar Python 3.11+, dependencias y comandos sin pasos ocultos.
2. Crear `.venv`, instalar requirements y ejecutar `python -m app.bootstrap`.
3. Confirmar que el bootstrap no requiere descargar el dataset ni modelos para pruebas
   locales.
4. Levantar Uvicorn y comprobar `/admin`, `/call`, `/health` y `/docs` desde el navegador.
5. En `/admin`, probar preview, disable, abstencion RAG, enable, recuperacion y delete; los
   snapshots historicos no se reutilizan como evidencia nueva.
6. Probar permisos de microfono, idioma `es-CO`, estados de escucha, audio del agente y fallback
   de texto. Un timeout ofrece reintento/texto y no crea un turno.
7. Ejecutar el recorrido de conocimiento vivo y guardar capturas/logs.
8. Documentar como detener el servidor y separar datos locales de las fuentes canonicas.

## Criterios de aceptacion

- [ ] Una persona con un entorno limpio puede levantar el sistema en <=15 minutos siguiendo
  [setup local](../../../readme/02_setup_local.md).
- [x] `/admin` permite subir, listar, previsualizar, habilitar/deshabilitar y eliminar un
  documento; muestra estado tecnico y publicacion separados.
- [ ] `/call` inicia una llamada de voz, recibe microfono y reproduce respuesta en espanol.
- [x] Una fuente cargada se usa antes del delete y se olvida despues, sin reinicio, en la
  prueba automatizada y la integracion local.
- [x] Las URLs, permisos, credenciales opcionales y fallbacks estan explicados.
- [x] La demo y el diagrama describen el comportamiento implementado; la ejecucion manual
  de voz aun no esta capturada.

## Verificacion y evidencia

Receta ejecutable desde la raiz y comandos de preflight:

```text
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.bootstrap --data-dir <temp>
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>
python -m pytest -q --basetemp <temp>
ruff check .
node --check app/web/app.js
```

El bootstrap del 2026-08-08 proceso 104 documentos: 103 `available` y 1 `needs_ocr`. El
focused admin/timeout paso 24 tests y la suite completa paso 96; Ruff y la sintaxis de
`app/web/app.js` no reportaron hallazgos. Sigue pendiente el cronometraje desde entorno limpio
para G2 y el smoke manual de `/call` con microfono y audio para G4. G5 tiene prueba automatizada
e integracion local verificadas, pero no evidencia de un documento externo al corpus en una demo.

## Dependencias

- Depende de todas las fases anteriores y de un navegador con Web Speech API compatible.
- Requiere una clave `GROQ_API_KEY` solo para la demo remota completa; el modo local
  extractivo debe seguir siendo auditable sin ella.
- Requiere conservar el modelo permitido y su version exacta en el informe.

## Estado

**Implementado y levantable localmente; preview/toggle/timeout probados. Cronometraje G2, voz
real, Groq/Whisper real y demo G5 externa pendientes (2026-08-08).**
