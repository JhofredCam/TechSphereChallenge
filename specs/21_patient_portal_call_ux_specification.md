# Spec: Rediseño UI/UX del portal de atención del paciente

**ID:** `PATIENT-PORTAL-UX-021`
**Estado:** `IMPLEMENTED`; portal conversacional, rail operativo y cierre integrados; smoke browser pendiente
**Versión:** 0.1.0
**Fecha:** 2026-08-09
**Propietario:** diseño visual y superficie `/call`
**Depende de:** [`11_conversational_ux_writing_specification.md`](11_conversational_ux_writing_specification.md), [`20_frontend_architecture_routing_demo_state_specification.md`](20_frontend_architecture_routing_demo_state_specification.md), [`06_system_flow_diagram_specification.md`](06_system_flow_diagram_specification.md)
**Coordina con:** [`22_audio_engine_continuous_vad_specification.md`](22_audio_engine_continuous_vad_specification.md)

## Objective

Rehacer `/call` para que la conversación sea la acción principal y el estado clínico operativo
permanezca visible al lado: triaje, trazabilidad de fuentes y cierre de la atención. La vista
debe servir a un paciente que necesita hablar con calma y a un evaluador que necesita verificar
qué ocurrió, sin convertir la pantalla en un panel técnico.

### Principios de experiencia

- La conversación ocupa el primer plano; el formulario de alta vive en la entrada de paciente.
- El paciente reconoce en todo momento si el sistema está escuchando, procesando o respondiendo.
- El triaje es visible como decisión y siguiente paso, nunca como color sin texto.
- La trazabilidad es adyacente y legible, pero no se pronuncia por TTS.
- El cierre permanece disponible durante la llamada, con confirmación para evitar cierres
  accidentales.
- El copy sigue la Spec 11: `patient_text`, burbuja y TTS deben ser idénticos.

## Design Direction — “Cartografía de recuperación”

El producto trata una conversación postoperatoria como un mapa de señales: una columna amplia
para lo que el paciente cuenta y una baliza lateral que resume el nivel de atención. La dirección
evita el dashboard hospitalario azul y el “chatbot genérico” de tarjetas flotantes.

### Token system

| Rol | Token | Uso |
|---|---|---|
| `ink` | `#153B3B` | texto, títulos y navegación |
| `paper` | `#F5F8F2` | fondo vivo, ligero y no clínicamente frío |
| `panel` | `#FCFBF7` | superficie de lectura |
| `signal` | `#D76B4A` | acción primaria y atención de voz |
| `trace` | `#2C7470` | fuentes, enlaces y progreso |
| `caution` | `#E5B85C` | estado amarillo, siempre con etiqueta |

El color no decide triaje: cada estado debe tener texto (`Atención inmediata`, `Contactar hoy`,
`Sin señales de alarma`, `Necesitamos aclarar`) e icono con nombre accesible.

### Tipografía

- Display: `Fraunces, Georgia, serif`, solo para el título de la sesión y la tesis de la vista.
- Lectura: `Atkinson Hyperlegible, ui-sans-serif, system-ui, sans-serif`, con altura de línea
  amplia para transcripciones y mensajes de cuidado.
- Utilitaria: `ui-monospace, SFMono-Regular, Consolas, monospace` solo para timestamps y revisión
  técnica, nunca para mensajes dirigidos al paciente.
- No se descarga una fuente durante bootstrap; los fallbacks deben mantener contraste y métricas.

### Signature element

La firma visual es el **rail de acompañamiento**: una línea vertical junto al panel lateral con un
punto de estado y una etiqueta verbal. El rail conecta conversación, decisión de triaje y cierre
como un único recorrido. No anima todo el dashboard: solo el punto de estado cambia al pasar por
`Escuchando`, `Procesando`, `Respondiendo` y `Atención cerrada`, respetando `prefers-reduced-motion`.

### Wireframe

```text
┌────────────────────────────────────────────────────────────────────┐
│ marca                         Llamada   Conocimiento   Salir       │
├────────────────────────────────────────────────────────────────────┤
│ Seguimiento de hoy                         [DEMO · es-CO]           │
│ “Estoy aquí para escucharte...”                                      │
├───────────────────────────────────────┬────────────────────────────┤
│ CONVERSACIÓN (primer plano)            │ RAIL DE ACOMPAÑAMIENTO     │
│                                       │ ● Estado de la llamada      │
│  asistente · mensaje canónico         │   Escuchando / Procesando   │
│  paciente · transcripción             │   / Respondiendo            │
│                                       │                              │
│  [micrófono: Hablar / Terminar]       │ TRIAJE                       │
│  Te escucho.                          │   Necesitamos aclarar       │
│  [escribir mensaje] [Enviar]          │   siguiente paso              │
│                                       │                              │
│                                       │ TRAZABILIDAD                 │
│                                       │   Guía · p. 2 · revisión 8    │
│                                       │                              │
│                                       │ CIERRE                       │
│                                       │   [Finalizar atención]       │
└───────────────────────────────────────┴────────────────────────────┘
```

En móvil el rail se convierte en bloques apilados con el estado de llamada primero, triaje
segundo, fuentes tercero y cierre al final. La conversación no queda debajo de un formulario.

## Tech Stack

- HTML semántico, CSS existente y JavaScript sin bundler; no introducir una librería visual para
  esta iteración.
- `app/web/call.html`, `app/web/app.js`, `app/web/messages.js` y `app/web/styles.css`.
- API existente para turnos, fuentes, triaje, eventos de voz, timing y cierre.
- `SpeechSynthesis` en `es-CO` como salida; el nuevo ciclo de voz se especifica en la Spec 22.
- Contraste mínimo WCAG 2.2 AA, foco visible, navegación de teclado, live regions acotadas y
  soporte de `prefers-reduced-motion`.

## Commands

```text
python -m pytest tests/test_conversational_ux.py tests/test_http_contracts.py -q
python -m pytest tests/test_triage.py tests/test_calls.py tests/test_timeout.py -q
node --check app/web/app.js
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
git diff --check
```

El smoke visual debe realizarse en Chrome o Edge con una sesión de paciente demo y registrarse
como evidencia manual; `node --check` no prueba layout ni micrófono.

## Project Structure

```text
app/web/call.html       -> estructura semántica: conversación + rail operativo
app/web/app.js          -> render de turnos, estados, triaje, fuentes y cierre
app/web/messages.js     -> copy canónico de voz y display
app/web/styles.css      -> tokens, grid, rail, responsive y focus states
tests/test_call_ui_contracts.py -> landmarks, aria, copy y ausencia de formulario de alta
tests/test_conversational_ux.py  -> paridad texto/audio, seguridad y mensajes
readme/06_bitacora_de_sesiones/ -> evidencia de smoke visual
```

## Component and State Contract

### Landmarks

- `<main>` contiene un `section` de conversación con `aria-labelledby`.
- El listado de turnos usa `role="log"`, `aria-live="off"` para no leer automáticamente el
  historial y un resumen de estado separado.
- El estado de audio usa `aria-live="polite"` y solo anuncia transiciones, no cada parcial.
- El rail contiene regiones con títulos: `Estado de la llamada`, `Triaje`, `Fuentes consultadas`
  y `Cierre de atención`.
- El botón de finalizar tiene texto de acción y confirmación; no se representa solo con un icono.

### State projection

| Estado | Vista primaria | Rail | Acción disponible |
|---|---|---|---|
| `idle` | invitación a comenzar | `Listo para escuchar` | `Hablar`, texto |
| `listening` | micrófono activo y parcial | `Escuchando` | `Terminar escucha` |
| `processing` | último mensaje + espera | `Procesando` | cancelar si no rompe idempotencia |
| `responding` | respuesta del agente | `Respondiendo` | `Finalizar atención` |
| `error` | fallback explicativo | `Necesita atención técnica` | `Reintentar`, texto |
| `finished` | resumen final | `Atención cerrada` | volver a inicio |

El estado clínico es independiente: `red`, `yellow`, `green`, `unknown`. Nunca se debe mapear
un estado de audio a un nivel de triaje.

### Panel de trazabilidad

Cada fuente se muestra como `filename`, página, cita y revisión con un texto corto. El componente
no inserta HTML proveniente del corpus y no expone score, prompt, SHA ni nombres de tablas al
paciente. El aviso “Fuentes consultadas” explica que la respuesta se basa en material disponible;
la respuesta hablada permanece natural.

## Code Style

Derivar toda la vista de un modelo pequeño y hacer explícita la proyección de estado:

```js
function renderCallState(state) {
  const labels = {
    idle: "Listo para escuchar",
    listening: "Escuchando",
    processing: "Procesando",
    responding: "Respondiendo",
    error: "Necesita atención técnica",
    finished: "Atención cerrada",
  };
  const label = labels[state] || labels.error;
  document.querySelector("#voice-state").textContent = label;
  document.querySelector("#call-rail").dataset.state = state;
}
```

Usar `textContent`, nombres en lenguaje humano, clases por estado y una sola función para
actualizar el rail. No mezclar la fuente de trazabilidad con `patient_text` ni presentar estados
internos como `LISTEN_TIMEOUT`.

## Testing Strategy

### Contrato automatizado

- verificar landmarks, orden de tabulación, `aria-live`, botón de cierre y textos en español;
- confirmar que la conversación precede visualmente al rail en desktop y que el formulario de alta
  no aparece en `/call`;
- comprobar que `display_text === voice_text === SpeechSynthesisUtterance.text`;
- comprobar que una fuente se muestra en trazabilidad y no se pronuncia;
- comprobar que `red` sigue mostrando atención inmediata y que `unknown` no se convierte en verde;
- verificar que los errores usan el catálogo y nunca `error.message` crudo.

### Visual y responsive

- Chrome/Edge a 1440×900: conversación dominante, rail visible sin scroll horizontal.
- 1024×768: columnas equilibradas, cierre visible.
- 390×844: bloques apilados, botón de voz de ancho útil, foco visible y lectura sin solapamiento.
- zoom 200% y teclado: ningún control queda fuera de viewport o sin nombre.
- `prefers-reduced-motion: reduce`: el rail cambia sin transiciones.

### Evidencia manual

Registrar fecha, navegador, viewport, permiso de micrófono, cada estado observado, audio emitido,
triaje, fuentes, cierre y limitaciones. No afirmar G4 con una prueba textual o un mock.

## Boundaries

- **Always:** priorizar la conversación, mostrar estado textual, conservar triaje determinista,
  separar fuentes de voz, mantener fallback de texto, escapar corpus, soportar teclado y reducir
  movimiento cuando se solicite.
- **Ask first:** cambiar el modelo de interacción a full-screen, agregar streaming WebRTC,
  alterar copy clínico, ocultar trazabilidad, introducir fuentes externas o agregar un sistema de
  diseño remoto.
- **Never:** convertir color en diagnóstico, hacer que las fuentes interrumpan el diálogo, leer
  chunks/score/SHA al paciente, ocultar alertas rojas, usar texto técnico como copy visible o
  declarar una prueba manual sin observación real.

## Success Criteria

| ID | Criterio verificable | Evidencia |
|---|---|---|
| `UX-AC-01` | conversación ocupa el primer plano y el formulario de alta no está en `/call` | HTML/CSS + smoke |
| `UX-AC-02` | triaje, trazabilidad y cierre permanecen visibles en desktop | smoke 1440×900 |
| `UX-AC-03` | el rail se apila correctamente en móvil sin perder acciones | smoke 390×844 |
| `UX-AC-04` | estados `Escuchando`, `Procesando`, `Respondiendo` son visibles y accesibles | contrato + voz |
| `UX-AC-05` | fuentes son trazables sin ser habladas | integración de paridad |
| `UX-AC-06` | alertas roja/amarilla y ambigüedad mantienen copy seguro y determinista | pruebas de triaje |
| `UX-AC-07` | foco, contraste, live regions y reduced motion cumplen el contrato | revisión manual + tests |
| `UX-AC-08` | la experiencia conserva el fallback textual y el aviso de demo | smoke |
| `UX-AC-09` | la evidencia de voz se separa de la evidencia de layout y no sobreafirma G4 | bitácora |

## Implementation Plan and Tasks

1. Dibujar la nueva estructura semántica de `call.html` y conservar IDs de API necesarios.
2. Extraer el alta al acceso definido en la Spec 20.
3. Implementar tokens, grid de conversación/rail, estados y responsive.
4. Proyectar triaje, fuentes y cierre desde el payload existente.
5. Añadir contratos de accesibilidad, paridad y copy.
6. Ejecutar smoke en tres tamaños, documentar evidencia y sincronizar `docs/arquitectura.md` y
   Spec 06.

## Open Questions

1. ¿El rail debe ser `position: sticky` en desktop? Se recomienda sí, limitado al contenedor para
   no ocultar el cierre ni producir una segunda barra de scroll.
2. ¿El cierre debe abrir un resumen antes de guardar o guardar directamente? Se recomienda
   confirmación con resumen visible y un único POST idempotente.
3. La selección final de fuentes tipográficas requiere validar licencias si se incorporan archivos
   en el repositorio; esta spec presupone stacks locales.
