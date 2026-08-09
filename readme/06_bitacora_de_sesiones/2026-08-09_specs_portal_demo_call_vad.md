# 2026-08-09 | Specs de portal demo, UX de llamada y VAD

## Alcance

Se descompuso el objetivo de reestructuración del portal en tres especificaciones correlativas:

- `specs/20_frontend_architecture_routing_demo_state_specification.md` — landing, rutas y
  estado demo por roles.
- `specs/21_patient_portal_call_ux_specification.md` — rediseño visual y accesible de `/call`.
- `specs/22_audio_engine_continuous_vad_specification.md` — llamada continua, VAD y silencio
  configurable.

También se propagaron referencias en `README.md`, `.env.example`, la vista normativa de la Spec
06, el contrato heredado de la Spec 05, la UX Writing de la Spec 11 y este índice de sesiones.

## Decisiones y supuestos

- La implementación prevista conserva FastAPI + HTML/CSS/JavaScript sin bundler; React/Zustand no
  se introduce por defecto porque no existe en el fork.
- La diferenciación Paciente/Admin es explícitamente mock: clave fija `12345`, `sessionStorage`,
  sin JWT, cookies, backend de usuarios ni afirmación de autenticación.
- El formulario de alta deja `/call` y pasa a la entrada del paciente; el contexto se propaga a
  `POST /api/calls` sin enviar la clave.
- La dirección visual de `/call` usa una conversación dominante y un rail lateral de estado,
  triaje, trazabilidad y cierre, con responsive, teclado y reduced motion.
- `VOICE_SILENCE_TIMEOUT_MS=2000` es el default propuesto para cerrar un segmento que sí contiene
  voz y texto confirmado. `PATIENT_LISTEN_TIMEOUT_MS` queda como watchdog técnico oculto y no como
  presión visible ni decisión clínica.
- La Spec 22 es sucesora de la parte contradictoria de las Specs 05 y 11; se mantienen la
  idempotencia, el fallback, la abstención, el triaje determinista y la paridad exacta entre
  texto visible y audio.

## Delegación y contingencia

Se lanzaron tres subagentes en paralelo con ámbitos de escritura separados para las Specs 20,
21 y 22, como pedía la sesión. Los tres terminaron con el límite de uso del entorno antes de
producir cambios; la redacción se completó localmente en la misma rama dedicada.

## Archivos tocados

- `specs/20_frontend_architecture_routing_demo_state_specification.md`
- `specs/21_patient_portal_call_ux_specification.md`
- `specs/22_audio_engine_continuous_vad_specification.md`
- `specs/05_patient_listening_timeout_specification.md`
- `specs/06_system_flow_diagram_specification.md`
- `specs/11_conversational_ux_writing_specification.md`
- `.env.example`
- `README.md`
- `readme/06_bitacora_de_sesiones/README.md`
- `readme/06_bitacora_de_sesiones/2026-08-09_specs_portal_demo_call_vad.md`

`AGENTS.md` ya estaba modificado al comenzar y se conserva fuera de este incremento.

## Verificación ejecutada

```text
git status --short --branch
git switch -c spec/portal-demo-call-vad
Get-Content ... (guía, contrato oficial, specs y runtime existentes)
```

La inspección confirmó que el runtime actual sirve `/` como `/call`, usa `/admin` directo,
mantiene `PATIENT_LISTEN_TIMEOUT_MS` y aún no tiene VAD, rutas de acceso demo ni `voice-loop.js`.
No se ejecutaron pruebas de código porque esta sesión solo crea y sincroniza especificaciones;
los comandos de implementación y verificación futura están definidos dentro de cada spec.

## Riesgos y pendientes

- Las nuevas capacidades siguen `PROPOSED`; no deben presentarse como implementadas ni como
  evidencia de G4.
- Hace falta decidir si `/admin` será la pantalla de acceso o si se añadirá una ruta separada
  `/admin/access`, manteniendo enlaces existentes.
- El VAD con Web Audio + Web Speech requiere validar permisos, ruido, carreras y retorno después
  de TTS en Chrome/Edge real.
- Antes de implementar, hay que actualizar `docs/arquitectura.md`, `mvp/deliverables/02_architecture/architecture.md`,
  tests, health/config pública y el flujo Mermaid de la Spec 06.

## Siguiente acción verificable

Revisar y aprobar las Specs 20-22; después implementar por dependencia: acceso/contexto, layout
de `/call`, y finalmente el controlador VAD con pruebas sintéticas, integración HTTP y smoke real.
