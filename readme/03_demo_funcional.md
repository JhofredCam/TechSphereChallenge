# Demo funcional

## Estado

Guion preparado; el servidor y las dos superficies ya existen. La ejecucion manual, las
capturas y el video siguen `PENDIENTES` al 2026-08-08. La demo debe usar el [setup local](02_setup_local.md) y el
[contrato de la rubrica](../docs/rubrica-evaluacion.md).

La prueba automatizada de conocimiento vivo y la integracion local upload/delete ya pasan,
pero no sustituyen la evidencia de G5 con un documento que no pertenezca al corpus entregado.

## Precondiciones

1. Servidor en `http://127.0.0.1:8000` levantado con `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
2. Bootstrap completado y corpus con estados visibles en `/admin`.
3. Chrome o Edge con microfono permitido para `127.0.0.1`.
4. Una clave `GROQ_API_KEY` solo si se va a demostrar el camino LLM/STT remoto; sin ella la
   interfaz usa SpeechRecognition y el agente usa el fallback extractivo local.
5. Documento de prueba externo al corpus entregado, con una frase unica y no clinicamente
   peligrosa, para la prueba de conocimiento vivo.

## Recorrido de consola

1. Abrir `/admin` y mostrar el listado inicial, incluyendo `available` y, si aplica,
   `needs_ocr`.
2. Subir el documento de prueba y esperar el estado `available` antes de consultarlo.
3. Usar en la llamada una pregunta que solo pueda responderse con la frase del documento.
   Mostrar la cita de documento, pagina o chunk.
4. Eliminar el documento desde la consola.
5. Repetir la pregunta sin reiniciar el servidor y mostrar abstencion o ausencia de la
   fuente eliminada. Esto prueba que el agente olvida en caliente.

## Recorrido de llamada

1. Abrir `/call`, iniciar una llamada y comprobar el permiso de microfono.
2. Decir un saludo y una pregunta trivial para cubrir G4.
3. Hacer una pregunta clinica cubierta por el corpus y verificar respuesta breve en espanol,
   fuente trazable y audio.
4. Hacer una pregunta sin evidencia y verificar abstencion explicita, no una recomendacion
   inventada.
5. Simular una entrada ambigua y verificar que el agente pide aclaracion.
6. Simular una senal de alarma y verificar alerta persistente, nivel no degradable y siguiente
   paso comunicado sin inventar dosis ni diagnosticos.
7. Cerrar la llamada y mostrar el resumen con paciente, procedimiento, sintomas, decision,
   fuentes, alerta y proximos pasos.

## Evidencia a capturar

- Hora y commit de la demo.
- Captura de `/admin` antes y despues del upload/delete.
- Registro de la consulta grounded y su cita.
- Registro de que la fuente desaparece despues del delete.
- Video o captura del microfono, transcripcion y audio de `/call`.
- Resumen final y alerta persistida.
- Logs y respuesta de `/api/metrics`, sin secretos.

No declarar una compuerta aprobada solo porque el recorrido esta escrito. La matriz de estado
esta en [metricas y evidencia](04_metricas_y_evidencia.md).

## Estado de las compuertas

- G2: `PENDIENTE` de cronometraje desde entorno limpio.
- G4: `PENDIENTE` de smoke manual con microfono, transcripcion y audio.
- G5: prueba automatizada e integracion local verificadas; `PENDIENTE` de evidencia con el
  documento externo en una demo.
