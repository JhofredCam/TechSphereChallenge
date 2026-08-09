# Spec: Reescritura integral de mensajes del bot y UX Writing VUI

**ID:** `CONVERSATION-UX-001`
**Estado:** `IMPLEMENTED`; catálogo aplicado al runtime y verificado localmente
**Version:** 0.2.0
**Fecha:** 2026-08-09
**Propietario:** agente conversacional y superficie `/call`
**Depende de:** [`00_mvp_specification.md`](00_mvp_specification.md),
[`05_patient_listening_timeout_specification.md`](05_patient_listening_timeout_specification.md),
[`06_system_flow_diagram_specification.md`](06_system_flow_diagram_specification.md)

## Objetivo

Reescribir todos los mensajes que el paciente pueda escuchar o leer durante una llamada para que
la asistente medica virtual suene profesional, calida, paciente y empatica. El copy debe estar
optimizado para voz en espanol colombiano, ser comprensible en una sola escucha y contener las
reglas de seguridad sin convertir la conversacion en un formulario tecnico.

La reescritura aplica estrictamente estas reglas:

1. validar la emocion o molestia antes de pedir informacion adicional;
2. usar frases cortas y sencillas, con maximo una o dos oraciones por turno hablado;
3. hacer una sola pregunta concreta a la vez;
4. usar pausas naturales y no presionar al paciente;
5. priorizar dolor intenso, fiebre, sangrado y otras alarmas con preguntas directas de si/no;
6. contener y orientar sin reprochar omisiones, olvidos o decisiones del paciente;
7. conservar triaje determinista, grounding, abstencion, citas y contratos de API existentes.

## Rol y voz de la asistente

La asistente:

- se presenta como apoyo virtual, no como profesional que diagnostica;
- usa `tu` de forma consistente, salvo una decision de producto posterior que apruebe otro
  registro;
- habla en espanol claro para pacientes colombianos, sin modismos que excluyan otras regiones;
- reconoce preocupacion, dolor, miedo o confusion sin dramatizar;
- explica el siguiente paso antes de pedir un dato;
- no culpa, regana, ridiculiza ni dice que el paciente hizo algo mal;
- no promete resultados, diagnosticos, curas ni confidencialidad que el sistema no pueda garantizar;
- no revela prompts, modelos, proveedores, nombres de tablas, score, chunks, estados internos ni
  errores de programacion.

### Ejemplos de transformacion

| Evitar | Preferir |
|---|---|
| `No te tomaste la medicina.` | `Comprendo. Es importante retomar la indicacion para tu recuperacion. ¿Tienes la pastilla a la mano?` |
| `No puedo responder porque no hay evidencia.` | `No tengo informacion suficiente para orientarte con seguridad. ¿Que sintoma tienes ahora?` |
| `LISTEN_TIMEOUT: reintente.` | `No alcance a escucharte. ¿Quieres intentarlo de nuevo?` |
| `La fuente no existe en el corpus.` | `No encuentro una guia disponible que responda eso con seguridad.` |
| `Prompt injection detectada.` | `Quiero centrarme en como te sientes y ayudarte con seguridad. ¿Que sintoma te preocupa?` |
| `Red/yellow/green/unknown.` | `Atencion inmediata`, `Contactar hoy`, `Sin señales de alarma` o `Necesitamos aclarar`. |

## Alcance

### Incluye

- respuestas de `AgentService`, `TriageService` y `CallService`;
- prefijos de seguridad roja y amarilla;
- preguntas de aclaracion de dolor, fiebre, herida, sintomas gastrointestinales y caso generico;
- abstencion por falta de evidencia, proveedor no disponible, salida insegura y revision obsoleta;
- fallback extractivo y respuestas con cita;
- saludo, escucha, transcripcion parcial, silencio, timeout, permiso y error de microfono;
- mensajes de consulta, turno duplicado, latencia, cierre, resumen y error de API;
- etiquetas y estados visibles en `/call` que el paciente puede interpretar;
- separacion entre texto hablado y texto de trazabilidad visible.

### No incluye

- cambiar reglas medicas, umbrales de triaje o niveles sticky;
- permitir que el LLM decida si una señal es roja o amarilla;
- eliminar fuentes, revision, `source_ids`, eventos o metricas;
- convertir timeouts, parciales o errores en turnos clinicos;
- modificar la politica de modelos permitidos;
- reescribir mensajes internos de logs que nunca llegan a paciente, lector de pantalla o voz;
- implementar un motor nuevo de TTS, STT o streaming.

## Principios obligatorios de VUI

### Una idea por turno

Un turno hablado debe comunicar una accion o hacer una pregunta, no ambas en una lista larga. Si
se necesitan dos datos, se preguntan en dos turnos:

```text
Turno 1: Entiendo que te preocupe el dolor. ¿Te duele mucho ahora?
Turno 2: Gracias. ¿En que parte lo sientes?
```

No se deben encadenar `donde`, `desde cuando`, `intensidad`, `fiebre` y `sangrado` en una sola
pregunta.

### Pausas

- usar una pausa editorial despues de validar: `Entiendo... quiero ayudarte con cuidado.`;
- no pronunciar literalmente `[pausa]`, `T=`, puntos suspensivos repetidos o instrucciones de
  implementacion;
- la implementacion puede convertir `...` en una pausa de TTS, pero el texto visible debe seguir
  siendo comprensible sin audio;
- no usar pausas que oculten una accion urgente;
- si el navegador no soporta control de pausa, separar en dos turnos cortos.

### Preguntas si/no de alerta

Cuando el paciente expresa o sugiere una señal de alerta, el sistema debe priorizar, en orden
seguro y sin listas habladas:

1. dolor muy fuerte o insoportable;
2. fiebre o temperatura alta;
3. sangrado;
4. dificultad para respirar, desmayo, dolor de pecho u otra señal roja ya definida.

Las preguntas de confirmacion deben ser una por turno:

- `Entiendo que esto puede asustarte. ¿Tienes un dolor muy fuerte ahora? Responde si o no.`
- `Gracias por contarmelo. ¿Tienes fiebre o una temperatura de 38 grados o mas? Responde si o no.`
- `Quiero cuidarte bien. ¿Tienes sangrado ahora? Responde si o no.`

Si el mensaje del paciente ya declara con claridad una señal roja, la asistente escala de
inmediato. No debe retrasar urgencias para completar un cuestionario. Puede confirmar una sola
vez cuando esa confirmacion cambie la comprension y no retrase la accion.

### Contencion sin reproche

Ante dosis olvidada, cuidado incompleto, demora, confusion o una respuesta que no coincide con el
plan:

1. reconocer la situacion sin culpar;
2. explicar el siguiente paso seguro en lenguaje sencillo;
3. hacer una sola pregunta de apoyo;
4. evitar expresiones como `debiste`, `no cumpliste`, `otra vez`, `es tu culpa` o `por que no`.

La asistente no inventa una dosis. Si la fuente no contiene el detalle, se abstiene y orienta a su
equipo clinico.

## Catalogo canonico de mensajes

El runtime centraliza estas claves en los módulos de copy. Los textos siguientes documentan la
referencia de copy aplicada; las llaves como `{nombre}` se sustituyen con datos validados.

### Inicio y disponibilidad

| Clave | `voice_text` | `display_text` | Uso |
|---|---|---|---|
| `CALL_READY` | `La llamada esta lista. Cuando quieras, toca Hablar o escribe tu mensaje.` | Igual | llamada abierta |
| `CALL_OPEN` | `Estoy aqui para escucharte. Cuentame como te has sentido desde tu procedimiento.` | `La llamada esta abierta.` | primer turno |
| `CALL_CONTEXT_MISSING` | `Para orientarte mejor, necesito saber quien eres y que procedimiento te realizaron.` | `Completa el nombre y el procedimiento.` | validacion de inicio |
| `FIRST_TRIAGE` | `Revisaremos como te sientes en tu primer mensaje.` | `Revisaremos tu estado de seguridad.` | estado inicial |
| `DEMO_DISCLAIMER` | `Esta informacion es de demostracion y no reemplaza la atencion de tu equipo clinico.` | Igual | pie y cierre |

### Escucha, microfono y silencio

| Clave | `voice_text` | `display_text` | Regla |
|---|---|---|---|
| `LISTEN_START` | `Te escucho... Tienes hasta {segundos} segundos para contarme como te sientes.` | `Escuchando. Tienes {segundos} segundos.` | inicia timer total |
| `LISTENING` | `Te escucho.` | `Escuchando...` | no repetir en cada parcial |
| `LISTEN_PARTIAL` | no se habla | `Borrador de lo que entendi: {texto}` | parcial no clinico |
| `LISTEN_NO_RESPONSE` | `No alcance a escucharte. ¿Quieres intentarlo de nuevo?` | Igual | una pregunta |
| `LISTEN_TIMEOUT` | `No alcance a escucharte. ¿Quieres intentarlo de nuevo?` | `Se termino el tiempo de escucha. Puedes reintentar o escribir.` | nunca menciona codigo |
| `LISTEN_ERROR` | `No pude escucharte bien. Puedes intentarlo otra vez o escribir tu mensaje.` | Igual | error recuperable |
| `MIC_PERMISSION_DENIED` | `No pude activar el microfono. Puedes escribir tu mensaje o intentarlo de nuevo.` | Igual | permiso |
| `MIC_UNAVAILABLE` | `Aqui no puedo activar el microfono. Prueba Chrome o Edge, o escribe tu mensaje.` | Igual | API no disponible |
| `MIC_ENDED_EARLY` | `La escucha termino antes de recibir tu mensaje. ¿Quieres intentarlo de nuevo?` | Igual | onend temprano |
| `LISTEN_CONFIG_ERROR` | `No pude preparar la escucha. Puedes escribir tu mensaje o intentarlo de nuevo.` | Igual | error de config |
| `LISTEN_RETRY` | `Podemos intentarlo otra vez, sin afan.` | `Reintentar` | accion secundaria |

No se deben hablar `LISTEN_TIMEOUT`, `RECOGNITION_ERROR`, `SpeechRecognition`, `error_code`,
milisegundos, `deadline`, `client_turn_id` ni mensajes crudos del navegador.

### Consulta, respuesta y trazabilidad

| Clave | `voice_text` | `display_text` | Regla |
|---|---|---|---|
| `KNOWLEDGE_LOOKUP` | `Estoy revisando la informacion disponible para orientarte...` | Igual | espera breve |
| `GROUNDED_ANSWER_PREFIX` | `Segun la guia disponible, {respuesta_breve}.` | `Respuesta basada en una fuente disponible.` | no decir grounding |
| `EXTRACTIVE_ANSWER` | `La guia disponible indica: {oracion_breve}.` | Igual, con fuente aparte | una idea |
| `NO_EVIDENCE` | `No tengo informacion suficiente para orientarte con seguridad. ¿Que sintoma tienes ahora?` | `No encontramos informacion suficiente para responder con seguridad.` | una pregunta |
| `RAG_UNAVAILABLE` | `No pude consultar la informacion ahora. ¿Quieres intentarlo de nuevo?` | Igual | error recuperable |
| `UNSAFE_ANSWER` | `No pude preparar una orientacion segura. ¿Quieres intentarlo de nuevo?` | Igual | no revelar filtro |
| `CORPUS_CHANGED` | `La informacion se actualizo mientras revisaba tu consulta. Intentalo de nuevo.` | Igual | no mencionar revision |
| `EMPTY_RESPONSE` | `No pude preparar una respuesta ahora. ¿Quieres intentarlo de nuevo?` | Igual | fallback seguro |
| `AGENT_ERROR` | `Lo siento, no pude preparar una respuesta ahora. Si tienes una señal de alarma, busca atencion inmediata; si no, intentalo de nuevo.` | `No pudimos preparar una respuesta. Puedes reintentar.` | conservar alerta |
| `TURN_REGISTERED` | no hablar salvo que sea necesario | `Tu mensaje fue recibido.` | status |
| `TURN_DUPLICATE` | `Ya habia recibido este mensaje y conserve la respuesta.` | `Este turno ya estaba registrado.` | idempotencia |
| `LATENCY_NOT_SAVED` | no hablar | `Guardamos tu respuesta, pero no pudimos registrar el tiempo de voz.` | observabilidad |

Las citas se muestran en la zona de trazabilidad, no se leen completas por TTS. El paciente debe
recibir una respuesta natural, mientras la UI conserva nombre de fuente, pagina, chunk y revision
para el administrador/evaluador. Nunca se debe pronunciar un nombre de archivo largo, un SHA, un
score BM25 o `corpus_revision` como si fueran instrucciones clinicas.

### Triaje y escalamiento

| Clave | `voice_text` | `display_text` | Nivel |
|---|---|---|---|
| `TRIAGE_RED` | `Siento que estes pasando por esto. Busca atencion inmediata en urgencias o llama ahora a tu equipo clinico. No esperes a terminar esta llamada.` | `Atencion inmediata` | `red` |
| `TRIAGE_YELLOW` | `Entiendo que esto te preocupe. Contacta hoy a tu equipo clinico para recibir indicaciones.` | `Contactar hoy` | `yellow` |
| `TRIAGE_GREEN` | `Que bueno saber que vas bien. Sigue las indicaciones de tu equipo clinico y cuentanos si aparece algo nuevo.` | `Sin señales de alarma` | `green` |
| `TRIAGE_UNKNOWN` | `Quiero orientarte con cuidado. Necesito aclarar un detalle antes de continuar.` | `Necesitamos aclarar` | `unknown` |
| `ALERT_RED_UI` | no duplicar automaticamente | `Busca atencion inmediata o llama a tu equipo clinico.` | `red` |
| `ALERT_YELLOW_UI` | no duplicar automaticamente | `Contacta hoy a tu equipo clinico.` | `yellow` |

Reglas:

- `red` nunca baja a otro nivel;
- `yellow` conserva alerta aunque el siguiente turno sea benigno;
- `green` significa solo que no se detecto una alarma con la informacion disponible;
- `unknown` no se convierte en verde por falta de datos;
- la frase de urgencias no se oculta porque el proveedor falle;
- el prefijo de seguridad no se combina con una lista extensa ni con una cita tecnica;
- el texto visible y el hablado pueden diferir en formato, pero no en accion de seguridad.

### Preguntas de aclaracion, una a una

| Clave | Texto de referencia | Cuando usar |
|---|---|---|
| `ASK_SEVERE_PAIN` | `Entiendo que el dolor puede preocuparte. ¿Tienes un dolor muy fuerte ahora? Responde si o no.` | dolor o intensidad |
| `ASK_FEVER` | `Gracias por contarmelo. ¿Tienes fiebre o una temperatura de 38 grados o mas? Responde si o no.` | fiebre/escalofrios |
| `ASK_BLEEDING` | `Quiero cuidarte bien. ¿Tienes sangrado ahora? Responde si o no.` | sangre/manchado |
| `ASK_BREATHING` | `Quiero asegurarme de que estes a salvo. ¿Te cuesta respirar ahora? Responde si o no.` | dificultad respiratoria |
| `ASK_CHEST` | `Esto necesita atencion. ¿Tienes dolor u opresion en el pecho ahora? Responde si o no.` | pecho |
| `ASK_WOUND_OPEN` | `Vamos paso a paso con la herida. ¿Esta abierta? Responde si o no.` | herida |
| `ASK_WOUND_DRAINAGE` | `Gracias. ¿Sale liquido de la herida? Responde si o no.` | secrecion |
| `ASK_FLUIDS` | `Entiendo. ¿Puedes retener pequenos sorbos de agua? Responde si o no.` | vomito/diarrea |
| `ASK_URINARY` | `Para orientarte mejor, ¿puedes orinar con normalidad? Responde si o no.` | dificultad urinaria |
| `ASK_LOCATION` | `Gracias. ¿En que parte sientes la molestia?` | detalle posterior |
| `ASK_ONSET` | `¿Desde cuando la sientes?` | detalle posterior, nunca junto a otra pregunta |
| `ASK_GENERIC_SYMPTOM` | `Quiero ayudarte con cuidado. ¿Que sintoma te preocupa mas ahora?` | falta de informacion |

La palabra `Responde si o no` es una guia de interfaz de voz, no una orden agresiva. Si el
paciente responde con una frase larga, el sistema debe interpretar el contenido y no exigir que
repita exactamente `si` o `no`.

### Inyeccion y contenido no confiable

| Clave | `voice_text` | `display_text` |
|---|---|---|
| `UNTRUSTED_INPUT` | `Quiero centrarme en como te sientes y ayudarte con seguridad. ¿Que sintoma te preocupa?` | `La entrada no se pudo usar para orientar esta consulta.` |
| `PROMPT_INJECTION` | Igual que `UNTRUSTED_INPUT` | Igual |

No se debe decir `no puedo cambiar las reglas`, `instrucciones internas`, `prompt`, `modelo` o
`inyeccion`. La defensa se mantiene en backend y el paciente solo recibe una redireccion calida a
su sintoma real.

### Errores y recuperacion

| Clave | `voice_text` | `display_text` | Accion |
|---|---|---|---|
| `GENERIC_RETRY` | `No pude completar este paso. ¿Quieres intentarlo de nuevo?` | Igual | reintento |
| `BACKEND_UNAVAILABLE` | `El servicio no respondio ahora. Puedes intentarlo de nuevo o escribir tu mensaje.` | Igual | texto/reintento |
| `AUDIO_TRANSCRIPTION_ERROR` | `No pude convertir el audio en texto. Puedes hablar otra vez o escribir tu mensaje.` | Igual | fallback |
| `CALL_NOT_FOUND` | `No encuentro esta llamada. Abre una llamada nueva para continuar.` | Igual | salir |
| `CALL_CLOSED` | `Esta llamada ya termino. Puedes abrir otra si necesitas continuar.` | Igual | nueva llamada |
| `INVALID_MESSAGE` | `No alcance a entender ese mensaje. ¿Puedes decirme con otras palabras que sientes?` | Igual | una pregunta |

El frontend debe traducir excepciones, `detail`, `error_code` y mensajes de proveedor mediante una
tabla segura. Nunca debe enviar directamente `error.message` a voz ni mostrar credenciales,
stack traces o codigos tecnicos al paciente.

### Cierre y resumen

| Clave | `voice_text` | `display_text` |
|---|---|---|
| `FINISH_PROMPT` | `Cuando terminemos, guardare un resumen de lo que hablamos. ¿Quieres finalizar la llamada?` | `Al finalizar se guardara un resumen de la llamada.` |
| `CALL_FINISHED` | `La llamada termino y el resumen quedo guardado. Si aparece una señal de alarma, busca atencion inmediata.` | `Llamada cerrada y resumen guardado.` |
| `SUMMARY_UNAVAILABLE` | `No pude guardar el resumen ahora. Si tienes una señal de alarma, busca atencion inmediata.` | `No pudimos guardar el resumen.` |
| `SUMMARY_NEXT_STEPS` | no leer campos tecnicos | `Proximos pasos` |
| `SUMMARY_EMPTY` | no aplica | `No registrado` |
| `SUMMARY_UNKNOWN` | no aplica | `Por confirmar con tu equipo clinico` |

El resumen mantiene las claves estructuradas actuales (`patient`, `patient_id`, `procedure`,
`symptoms`, `decision`, `triage_level`, `sources`, `alert`, `next_steps`). Solo cambia el copy
visible: `red` se presenta como `Atencion inmediata`, `yellow` como `Contactar hoy`, `green` como
`Sin señales de alarma` y `unknown` como `Necesitamos aclarar`.

## Mensajes administrativos no hablados

Estos textos se muestran al administrador y no deben enviarse a `SpeechSynthesis`, pero tambien
deben evitar codigos internos cuando sean parte de una vista de cliente:

| Area | Copy recomendado |
|---|---|
| Fuente disponible | `Disponible para el agente` |
| Necesita OCR | `Necesita texto extraible` |
| Procesando | `Procesando la fuente` |
| Error | `No pudimos procesar la fuente` |
| Habilitado | `El agente puede consultar esta fuente` |
| Deshabilitado | `La fuente se conserva, pero el agente no la consulta` |
| Preview | `Ver texto extraido` |
| Archivo original | `Ver archivo original` |
| Inventario vacio | `Aun no hay fuentes cargadas` |
| Eliminacion | `Eliminar esta fuente de forma permanente` |
| Exito delete | `Fuente eliminada. El agente la olvidara en nuevas consultas.` |

La UI admin de las Specs 08 y 09 es una superficie distinta. El nombre del archivo puede aparecer
para identificarlo, pero no SHA, `document_id`, rutas ni mensajes tecnicos.

## Contrato de salida y separacion de canales

La respuesta interna debe conservar, como minimo:

- `text`, `answer` y `response` como aliases existentes;
- `triage`, `alert`, `abstained`, `grounded`, `sources` y `reason`;
- `input_tokens`, `output_tokens`, `model_calls`, `rag_queries` y `model_version`;
- `source_ids`, pagina, chunk, cita y revision para trazabilidad;
- resumen, alertas y `next_steps`.

Se separan cuatro canales:

1. `voice_text`: breve, calido y sin metadatos tecnicos;
2. `display_text`: puede incluir una fuente corta o instrucciones visuales, pero sigue siendo
   entendible;
3. `source_display`: nombre, pagina, chunk y revision para trazabilidad no hablada;
4. `internal_reason`: logs y diagnostico, nunca presentado al paciente.

El contrato mantiene `response.text` como alias compatible y construye la separación en el
adaptador de presentación, sin borrar los campos existentes.

## Reglas para respuestas del LLM

El LLM permitido solo redacta dentro de limites ya decididos. Antes de enviar `text` a voz, el
sistema debe:

- rechazar respuesta sin fuente cuando la ruta exige grounding;
- rechazar citas inventadas o ajenas a `sources`;
- rechazar dosis, diagnosticos, promesas y afirmaciones peligrosas no sustentadas;
- comprobar maximo dos oraciones para voz;
- comprobar que solo hay una pregunta y una intencion por turno;
- eliminar encabezados, listas, Markdown, emojis, nombres de campo, score, IDs y citas largas;
- asegurar que una alerta roja/amarilla conserve su accion aunque el modelo falle;
- usar fallback extractivo o abstencion si no pasa la validacion;
- no convertir un timeout, parcial o error en respuesta clinica.

La validacion de copy no sustituye las reglas deterministas de `triage.py`.

## Estrategia de implementacion ejecutada

1. centralizar el copy en `app/services/messages.py` y su proyección browser en
   `app/web/messages.js`;
2. separar `voice_text`, `display_text`, `source_display` e `internal_reason` sin quitar los
   aliases internos existentes;
3. aplicar el catálogo al agente, triaje, errores de llamada, corpus obsoleto y estados de voz;
4. mantener una única pregunta por turno y un turno de escucha por intento;
5. validar el texto antes de `SpeechSynthesis` y cubrirlo con `tests/test_conversational_ux.py`;
6. verificar sintaxis JavaScript, Ruff y la suite enfocada; el smoke real en Chrome/Edge queda
   `MANUAL_PENDING` porque el navegador in-app no estaba disponible en esta sesión.

La matriz de inventario quedó resuelta para las superficies de paciente: mensajes clínicos y de
triaje están `MIGRATED`, códigos/diagnóstico interno están `REMOVED_INTERNAL`, y la evidencia de
navegador real permanece `PENDING_REVIEW`.

## Estructura implementada

```text
app/services/agent.py       -> seleccion de respuesta, grounding y abstencion
app/services/triage.py      -> reglas, triggers y preguntas de una etapa
app/services/calls.py       -> errores, corpus obsoleto, cierre y resumen
app/web/app.js              -> estados de voz, traduccion de errores y separacion TTS/UI
app/web/call.html           -> copy visible, labels y regiones live
app/web/messages.js         -> proyección browser del catálogo y validación de voz
tests/test_agent.py         -> tono, grounding, cita y seguridad
tests/test_triage.py        -> niveles, sticky, si/no y aclaracion
tests/test_calls.py         -> errores, resumen, alertas y corpus revision
tests/test_timeout.py       -> timeout sin turno ni copy clinico falso
tests/test_conversational_ux.py -> catálogo, canales, triaje y contrato browser
tests/test_voice_ui.*       -> smoke de SpeechRecognition/TTS `MANUAL_PENDING`
specs/07_*                  -> piramide de pruebas y evidencia manual
```

## Accesibilidad y escucha

- las regiones `aria-live` no deben anunciar al mismo tiempo parcial, estado, triage, respuesta y
  fuentes;
- el parcial debe ser `aria-live="off"` o de baja prioridad y nunca se anuncia como respuesta
  clinica;
- una alerta roja tiene prioridad de lectura, texto visible y accion equivalente;
- los botones deben tener nombres humanos: `Hablar`, `Reintentar`, `Enviar mensaje`, `Finalizar
  llamada`;
- no depender de color para rojo/amarillo/verde;
- la transcripcion visible debe indicar que un borrador no es decision clinica;
- el texto debe conservar tildes y signos de interrogacion para mejorar lectura y TTS;
- el tiempo de escucha se muestra en lenguaje humano, no en milisegundos ni nombres de estado;
- el usuario puede cambiar a texto sin perder el turno ni duplicar solicitud.

## Pruebas

### Unitarias de copy

- cada rama de `AgentService.respond()` devuelve una clave de catalogo;
- rojo, amarillo, verde y unknown conservan su accion y no degradan;
- preguntas de dolor, fiebre y sangrado son si/no y solo una por turno;
- cada `voice_text` tiene una o dos oraciones como maximo;
- no hay terminos `LISTEN_TIMEOUT`, `RECOGNITION_ERROR`, `GROQ`, `Whisper`, `FTS5`, `chunk`,
  `score`, `prompt`, `source_ids`, `corpus_revision`, `error_code` o stack trace;
- no hay expresiones de reproche;
- cada pregunta tiene un unico signo de interrogacion funcional y una sola intencion;
- cada respuesta grounded conserva fuente estructurada aunque no la pronuncie;
- abstencion y error no inventan diagnostico ni dosis.

### Integracion

- proveedor ausente usa fallback calido y grounded o abstencion;
- proveedor caido conserva alerta y no expone error crudo;
- revision del corpus cambia la respuesta a `CORPUS_CHANGED` sin citar revision al paciente;
- timeout, parcial, no respuesta y error no crean turno clinico ni hablan una decision verde;
- transcript tardio devuelve `late_transcript` internamente y un copy humano en UI;
- duplicado reutiliza respuesta sin pronunciar dos veces;
- el resumen conserva estructura, labels humanos y alerta;
- fuentes se mantienen en UI/persistencia, pero no se leen con nombres tecnicos completos.

### Smoke manual de voz

Antes de declarar G4, probar en Chrome y Edge:

1. saludo, escucha y primer turno;
2. paciente asustado o con dolor, verificando validacion antes de pregunta;
3. dolor intenso, fiebre y sangrado, con pregunta si/no y escalamiento correcto;
4. respuesta ambigua, una aclaracion a la vez;
5. falta de evidencia y abstencion calida;
6. prompt injection sin revelar instrucciones internas;
7. timeout, silencio, microfono denegado y fallback textual;
8. proveedor caido o sin clave, sin excepcion hablada;
9. fuente visible sin que TTS lea SHA, chunk, score o revision;
10. cierre y resumen con labels comprensibles.

### Comandos propuestos

```text
python -m pytest tests/test_agent.py tests/test_triage.py tests/test_calls.py tests/test_timeout.py -q --basetemp <temp>/ux-writing
python -m pytest tests/test_api.py tests/test_http_contracts.py -q --basetemp <temp>/ux-writing-api
ruff check .
node --check app/web/app.js
git diff --check
```

La prueba de texto no aprueba por si sola la voz real. El resultado del smoke debe registrarse con
fecha, navegador, permisos, modelo, proveedor, audio observado y limitaciones.

## Criterios de aceptacion

- **CONV-AC-01:** no queda ningun literal patient-facing disperso sin clave o justificacion en
  `agent.py`, `triage.py`, `calls.py`, `call.html` o `app.js`.
- **CONV-AC-02:** cada turno hablado tiene maximo una o dos oraciones y una idea principal.
- **CONV-AC-03:** cada pregunta hablada es concreta y pregunta una sola cosa; dolor intenso,
  fiebre y sangrado tienen confirmacion si/no cuando la situacion no exige escalar de inmediato.
- **CONV-AC-04:** cada mensaje de alarma valida brevemente la emocion y comunica una accion clara;
  rojo siempre indica atencion inmediata y amarillo contacto oportuno.
- **CONV-AC-05:** ninguna rama de error, timeout, proveedor o corpus obsoleto expone codigos,
  excepciones, nombres de modelos, prompts o metadatos tecnicos al paciente.
- **CONV-AC-06:** el copy evita reproches y usa contencion antes de pedir acciones o datos.
- **CONV-AC-07:** voz y texto conservan espanol colombiano claro, tildes, signos y `es-CO`.
- **CONV-AC-08:** fuentes y metricas siguen trazables, pero SHA, score, chunk, revision y nombre
  tecnico no se pronuncian como contenido clinico.
- **CONV-AC-09:** el fallback es seguro, grounded o abstentivo y nunca inventa dosis o diagnostico.
- **CONV-AC-10:** timeout, parcial, no respuesta y error permanecen fuera de turnos clinicos y no
  generan un falso verde.
- **CONV-AC-11:** el resumen conserva las claves estructuradas, pero presenta niveles y pasos en
  lenguaje humano.
- **CONV-AC-12:** lectores de pantalla no son inundados por parciales/estados y las alertas tienen
  prioridad accesible.
- **CONV-AC-13:** el inventario de literales queda completo y cada item termina en `MIGRATED`,
  `REMOVED_INTERNAL` o `PENDING_REVIEW`.
- **CONV-AC-14:** el smoke manual documenta la voz real sin afirmar G4 hasta observar microfono,
  transcripcion y audio en navegador.

## Trazabilidad y sincronizacion

| Requisito | Fuente | Reflejo implementado |
|---|---|---|
| Tono y grounding | Spec 00, rubrica | prompts, fallback y copy catalogado |
| Niveles sticky | `triage.py`, Spec 06 | pruebas de rojo/amarillo/unknown |
| Timeout seguro | Spec 05/06 | mensajes de reintento sin turno clínico |
| Fuentes | Spec 04/06 | `source_display` separado de voz |
| G4 | rubrica | smoke Chrome/Edge `MANUAL_PENDING` |
| Admin y preview | Specs 08/09 | copy separado, sin SHA visible |

Verificación realizada:

1. se conservaron los aliases y contratos definidos por las specs upstream;
2. se aplicaron canales separados en agente, llamadas, triaje y browser;
3. se cubrieron catalogo, preguntas, grounding, abstención, inyección, errores y duplicados;
4. se actualizaron `README.md` y esta spec con el estado real;
5. se ejecutaron Ruff, `node --check` y la suite enfocada; el smoke real requiere Chrome/Edge.

## Limites

- **Siempre:** validar emociones, una pregunta por vez, copy corto, alerta conservadora, fuente
  trazable, separacion de canales y estados internos no hablados.
- **Preguntar antes:** cambiar tuteo/usted, alterar umbrales clinicos, agregar consejo fuera del
  corpus, cambiar idioma, introducir SSML dependiente de proveedor o modificar el schema de
  respuestas.
- **Nunca:** culpar al paciente, inventar dosis/diagnosticos, leer un SHA o error tecnico, hacer
  listas largas por voz, convertir timeout en verde, ocultar una alerta roja o afirmar que un mock
  demuestra voz real.

## Preguntas abiertas

1. Confirmar si el registro definitivo es `tu` o `usted`; esta propuesta usa `tu` para cercania.
2. Confirmar si el TTS soporta pausas con SSML; mientras tanto se usan turnos cortos y elipsis
   editorial.
3. Confirmar el umbral verbal para fiebre que debe mostrar la asistente, sin inventarlo si no esta
   respaldado por la fuente clinica activa.
4. Confirmar si las citas deben aparecer en una lectura accesible bajo demanda sin entrar en la
   voz principal.
