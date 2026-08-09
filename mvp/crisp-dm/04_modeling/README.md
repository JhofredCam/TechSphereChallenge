# 04 - Modeling

## Objetivo

Construir la respuesta conversacional grounded y la decision de escalamiento del MVP. El
modelo debe hablar en espanol, usar solo contexto recuperado, abstenerse sin evidencia y
dejar la seguridad clinica fuera de la autoridad exclusiva del LLM.

## Entradas

- Chunks y fuentes de [Data Preparation](../03_data_preparation/README.md).
- [Contrato de llamadas, resumen y triaje](../../../specs/00_mvp_specification.md#criterios-de-exito).
- [Familias permitidas](../../../docs/stack-tecnico.md#1-los-modelos-permitidos).
- [Plan de componentes](../../../specs/01_implementation_plan.md#componentes-y-dependencias).
- [Timeout configurable de escucha](../../../specs/05_patient_listening_timeout_specification.md).
- [Diagrama normativo del flujo](../../../specs/06_system_flow_diagram_specification.md).

## Salidas

- Adaptador de razonamiento configurado para `llama-3.1-8b-instant` via Groq, familia Meta
  Llama permitida; sin clave se usa el camino extractivo local.
- Modo extractivo determinista con SQLite FTS5 si `GROQ_API_KEY` no esta disponible.
- Prompt y contrato que delimitan el contexto clinico como datos no ejecutables y exigen
  citas, respuesta breve, empatia y abstencion.
- Triaje determinista: `rojo` no baja, `amarillo` persiste alerta y `unknown` pide aclaracion.
- Turnos, resumen de llamada, logs de latencia/tokens y respuesta hablada en el navegador.
- STT remoto opcional `whisper-large-v3`; no es el modelo de razonamiento.
- Escucha por turno con `PATIENT_LISTEN_TIMEOUT_MS`, estados parciales/timeout/error y fallback
  textual; `client_turn_id` y `listen_id` evitan duplicados y transcript tardio.

## Tareas concretas

1. Implementar recuperacion FTS5 y pasar al agente solo chunks activos con fuente y pagina.
2. Separar la normalizacion y las reglas de triaje de la salida generativa.
3. Configurar el adaptador OpenAI-compatible de Groq, el timeout y el manejo de cuota o
   modelo no disponible.
4. Crear una respuesta que no invente dosis, diagnosticos ni instrucciones fuera del corpus.
5. Implementar abstencion explicita cuando no existe evidencia suficiente.
6. Proteger el contexto contra instrucciones de documentos o pacientes que contradigan la
   mision del agente.
7. Conectar reconocimiento `es-CO`, entrada textual de fallback y `SpeechSynthesis` del
   navegador.
8. Registrar cada invocacion, consulta RAG, tokens y latencia con el identificador de llamada.
9. Mantener el timeout de escucha del paciente separado de Groq, Whisper y SQLite, registrar
   `POST /api/calls/{id}/voice-events` y reflejar el contrato en el diagrama.

## Criterios de aceptacion

- [x] El modelo configurado pertenece a una familia permitida y el informe declara nombre,
  version, proveedor y razon de eleccion.
- [x] Una respuesta clinica contiene una fuente recuperada o una abstencion clara.
- [x] El borrado de conocimiento no deja citas disponibles en respuestas nuevas.
- [x] Una senal roja nunca se degrada; una ambigua pide aclaracion antes de cerrar.
- [ ] La interfaz acepta microfono en Chrome/Edge, muestra transcripcion y reproduce audio en
  espanol, con fallback textual auditable.
- [x] Los logs exponen los campos necesarios para las metricas obligatorias.
- [x] La escucha configurable valida `PATIENT_LISTEN_TIMEOUT_MS`, publica el valor en `/health`,
  ofrece reintento/fallback seguro y rechaza transcript tardio; el smoke browser sigue pendiente.

## Verificacion y evidencia

Comandos automatizados ejecutados desde la raiz:

```text
python -m pytest -q --basetemp <temp>
ruff check .
node --check app/web/app.js
```

Resultado del 2026-08-08: 96 tests pasaron, Ruff no reporto hallazgos y la sintaxis de
`app/web/app.js` fue valida. Los tests cubren fallback extractivo, abstencion, adapter Groq
mediante contrato, filtrado de salida insegura, triaje, resumen, fuentes, metricas, timeout,
eventos e idempotencia. El uso remoto del proveedor no se ejercito porque es opcional y requiere
`GROQ_API_KEY`.

Evidencia manual pendiente: intercambio en `/call`, pregunta con fuente, pregunta sin
evidencia, entrada ambigua y senal roja usando microfono y audio reales. Los tests no
aprueban G4 por si solos.

## Dependencias

- Depende de ingestion/FTS5 y los contratos de llamadas de la fase 03.
- Depende de una familia permitida; cualquier cambio de proveedor o modelo debe actualizar
  configuracion, informe y evidencia juntos.
- La voz requiere permisos del navegador y puede necesitar `GROQ_API_KEY` para STT/LLM remoto.

## Estado

**Modelo y servicios implementados; pruebas automatizadas verificadas y smoke de voz, Groq y
Whisper reales pendientes (2026-08-08).**
