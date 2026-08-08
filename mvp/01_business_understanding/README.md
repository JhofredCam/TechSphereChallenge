# 01 - Business Understanding

## Objetivo

Convertir el reto en un alcance verificable para un agente de seguimiento postoperatorio
en espanol, dirigido a pacientes colombianos. La fase fija que problema resuelve el MVP,
que no intenta resolver y como se demostrara que las dos superficies funcionan.

## Entradas

- [README del reto](../../README.md), incluido el contrato de las dos superficies.
- [Especificacion del MVP](../../specs/00_mvp_specification.md).
- [Rubrica y compuertas G1-G5](../../docs/rubrica-evaluacion.md).
- [Familias de modelos permitidas](../../docs/stack-tecnico.md).
- Restriccion operativa de levantar el sistema en 15 minutos o menos.

## Salidas

- Alcance del MVP: consola `/admin` e interfaz `/call` con microfono y audio.
- Criterios de exito para RAG, aprendizaje/olvido, triaje, resumen y metricas.
- Modelo de razonamiento seleccionado: `llama-3.1-8b-instant` via Groq, familia Meta
  Llama permitida; queda configurado en el adaptador y existe un fallback local extractivo.
- Limites explicitos: sin telefonia real, integracion hospitalaria, autenticacion empresarial
  ni cobertura clinica universal.
- Matriz de aceptacion y evidencia que se completa en las fases 05 y 06.

## Tareas concretas

1. Identificar al paciente, su procedimiento, sintomas, nivel de riesgo y siguiente paso como
   informacion minima de una llamada.
2. Separar los contratos de administracion y llamada: subir/listar/eliminar documentos por
   un lado; iniciar llamada, hablar y escuchar al agente por el otro.
3. Fijar que toda respuesta clinica debe tener fuente recuperada o debe abstenerse.
4. Definir que el triaje determinista puede elevar el nivel, nunca degradar una senal roja,
   y debe pedir aclaracion ante ambiguedad.
5. Definir el resumen de cierre: paciente, procedimiento, sintomas, decision, fuentes,
   alerta y proximos pasos.
6. Registrar como metricas obligatorias P50/P95 de latencia, tokens de entrada/salida,
   invocaciones al modelo, consultas RAG y costo estimado por llamada.
7. Mantener separados los datos sinteticos del reto y cualquier conocimiento cargado desde
   la consola.

## Criterios de aceptacion

- [x] El alcance, los no-objetivos y las dos superficies estan descritos en la
  [especificacion del MVP](../../specs/00_mvp_specification.md).
- [x] Las compuertas de voz, conocimiento vivo, modelo permitido y levantamiento estan
  identificadas en la [rubrica](../../docs/rubrica-evaluacion.md).
- [x] Existe una aplicacion ejecutable que satisface el contrato sin depender de telefonia
  real: `app.main` expone `/admin`, `/call` y la API local.
- [ ] Existe evidencia reproducible de la demo, las metricas y las cinco compuertas.

## Verificacion y evidencia

Comando de verificacion documental desde la raiz:

```text
python -c "from pathlib import Path; required = ['README.md', 'specs/00_mvp_specification.md', 'docs/rubrica-evaluacion.md', 'docs/stack-tecnico.md']; assert all(Path(p).is_file() for p in required)"
```

La evidencia de runtime se captura en [metricas y evidencia](../../readme/04_metricas_y_evidencia.md)
y en [el informe final](../../docs/informe-final.md). En este corte la suite automatizada,
la validacion del dataset y el bootstrap estan verificados; la demo manual, el cronometraje
y la evidencia de las compuertas de voz siguen `PENDIENTE`.

Verificacion de runtime local:

```text
python -m pytest -q --basetemp <temp>
ruff check .
```

Resultado del 2026-08-08: 38 tests pasaron y Ruff no reporto hallazgos.

## Dependencias

- Fase 01 depende del contrato del reto, la especificacion y la rubrica.
- Las fases 02-06 dependen de este alcance para no mezclar capas, superficies ni criterios.
- La seleccion exacta de version del proveedor debe revisarse antes de una demo porque los
  identificadores de modelos pueden retirarse.

## Estado

**Implementado - contrato y runtime local verificados; demo y metricas de voz pendientes
(2026-08-08).**
