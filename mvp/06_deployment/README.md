# 06 - Deployment

## Objetivo

Dejar el MVP levantable localmente y demostrable desde un navegador, con una ruta operativa
que el jurado pueda seguir en 15 minutos o menos. Deployment aqui significa ejecucion local
reproducible, no telefonia ni despliegue hospitalario.

## Entradas

- [Setup local](../../readme/02_setup_local.md).
- [Guion de demo](../../readme/03_demo_funcional.md).
- Componentes de aplicacion definidos en la [especificacion](../../specs/00_mvp_specification.md#estructura-del-proyecto).
- Evidencia y criterios de [Evaluation](../05_evaluation/README.md).
- [Diagrama de arquitectura](../../docs/arquitectura.md).

## Salidas

- Entorno Python reproducible con dependencias declaradas en `requirements.txt`.
- Bootstrap local que crea base, valida dataset y procesa el corpus sin descargar datos.
- Servidor FastAPI/Uvicorn accesible en `127.0.0.1:8000`.
- `/admin` para upload, listado, estado `available`/`needs_ocr` y delete.
- `/call` para llamada browser/API con microfono, transcripcion, respuesta y audio.
- Instrucciones de permisos, fallback textual, variables de entorno y limpieza segura.
- Registro del tiempo real de setup y resultado de cada recorrido de demo.

## Tareas concretas

1. Declarar Python 3.11+, dependencias y comandos sin pasos ocultos.
2. Crear `.venv`, instalar requirements y ejecutar `python -m app.bootstrap`.
3. Confirmar que el bootstrap no requiere descargar el dataset ni modelos para pruebas
   locales.
4. Levantar Uvicorn y comprobar las dos URLs desde Chrome o Edge.
5. Probar permisos de microfono, idioma `es-CO`, audio del agente y fallback de texto.
6. Ejecutar el recorrido de conocimiento vivo y guardar capturas/logs.
7. Documentar como detener el servidor y separar datos locales de las fuentes canonicas.

## Criterios de aceptacion

- [ ] Una persona con un entorno limpio puede levantar el sistema en <=15 minutos siguiendo
  [setup local](../../readme/02_setup_local.md).
- [x] `/admin` permite subir, listar y eliminar un documento y muestra su estado real.
- [ ] `/call` inicia una llamada de voz, recibe microfono y reproduce respuesta en espanol.
- [x] Una fuente cargada se usa antes del delete y se olvida despues, sin reinicio, en la
  prueba automatizada y la integracion local.
- [x] Las URLs, permisos, credenciales opcionales y fallbacks estan explicados.
- [x] La demo y el diagrama describen el comportamiento implementado; la ejecucion manual
  de voz aun no esta capturada.

## Verificacion y evidencia

Comandos reales desde la raiz:

```text
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.bootstrap --data-dir <temp>
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

El bootstrap del 2026-08-08 proceso 104 documentos: 103 `available` y 1 `needs_ocr`. La
suite local y el recorrido automatizado de upload/delete pasaron. Sigue pendiente el
cronometraje desde entorno limpio para G2 y el smoke manual de `/call` con microfono y audio
para G4. G5 tiene prueba automatizada e integracion local verificadas, pero no evidencia de
un documento externo al corpus en una demo.

## Dependencias

- Depende de todas las fases anteriores y de un navegador con Web Speech API compatible.
- Requiere una clave `GROQ_API_KEY` solo para la demo remota completa; el modo local
  extractivo debe seguir siendo auditable sin ella.
- Requiere conservar el modelo permitido y su version exacta en el informe.

## Estado

**Implementado y levantable localmente; cronometraje y demo manual pendientes (2026-08-08).**
