# Demo funcional

## Estado

Guion preparado; el servidor y las dos superficies ya existen. La ejecucion manual, las
capturas y el video siguen `PENDIENTES` al 2026-08-08. La demo debe usar el [setup local](02_setup_local.md) y el
[contrato de la rubrica](../docs/rubrica-evaluacion.md).

La prueba automatizada de conocimiento vivo, preview, toggle y la integracion local
upload/delete ya pasan, pero no sustituyen la evidencia de G5 con un documento que no pertenezca
al corpus entregado.

## Precondiciones

1. Servidor en `http://127.0.0.1:8000` levantado con `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
2. Bootstrap completado y corpus con estados visibles en `/admin`.
3. Chrome o Edge con microfono permitido para `127.0.0.1`.
4. Una clave `GROQ_API_KEY` solo si se va a demostrar el camino LLM/STT remoto; sin ella la
   interfaz usa SpeechRecognition y el agente usa el fallback extractivo local.
5. Documento de prueba externo al corpus entregado, con una frase unica y no clinicamente
   peligrosa, para la prueba de conocimiento vivo.

El timeout configurable de escucha esta implementado y documentado en la
[spec de timeout](../specs/05_patient_listening_timeout_specification.md); la demo debe
distinguirlo de un timeout de proveedor. Las acciones de preview, habilitar, deshabilitar y
delete estan implementadas en la [spec de admin](../specs/04_admin_document_lifecycle_specification.md).

## Recorrido de consola

1. Abrir `/admin` y mostrar el listado inicial, incluyendo `available` y, si aplica,
   `needs_ocr`.
2. Subir el documento de prueba y esperar el estado `available` y publicacion `Habilitado`.
3. Abrir `Previsualizar` y mostrar el texto extraido literal, sin ejecutar Markdown/HTML.
4. Usar en la llamada una pregunta que solo pueda responderse con la frase del documento.
   Mostrar la cita de documento, pagina o chunk.
5. Deshabilitar el documento sin borrarlo y repetir la pregunta; debe excluirse del RAG y
   abstenerse.
6. Habilitarlo de nuevo, repetir la pregunta y mostrar recuperacion sin reingesta.
7. Eliminar el documento desde la consola y repetir la pregunta sin reiniciar; debe abstenerse
   y no mostrar esa fuente. Esto prueba que SQLite, FTS5 y, cuando el upgrade este activo, Chroma
   olvidan en caliente.

## Recorrido de llamada

1. Abrir `/call`, iniciar una llamada y comprobar el permiso de microfono.
2. Consultar `/health` y anotar `patient_listen_timeout_ms`; el limite es total por turno y no
   cambia Groq, Whisper ni SQLite.
3. Decir un saludo y una pregunta trivial para cubrir G4.
4. Hacer una pregunta clinica cubierta por el corpus y verificar respuesta breve en espanol,
   fuente trazable y audio.
5. Dejar vencer un turno o producir un parcial; verificar `LISTEN_TIMEOUT`/`RETRY_REQUIRED`,
   ausencia de turno clinico y opcion de reintentar o escribir. Un transcript tardio no abre otro
   turno.
6. Hacer una pregunta sin evidencia y verificar abstencion explicita, no una recomendacion
   inventada.
7. Simular una entrada ambigua y verificar que el agente pide aclaracion.
8. Simular una senal de alarma y verificar alerta persistente, nivel no degradable y siguiente
   paso comunicado sin inventar dosis ni diagnosticos.
9. Cerrar la llamada y mostrar el resumen con paciente, procedimiento, sintomas, decision,
   fuentes, alerta y proximos pasos.

## Evidencia a capturar

- Hora y commit de la demo.
- Captura de `/admin` antes y despues del upload, preview, disable/enable y delete.
- Registro de la consulta grounded y su cita.
- Registro de abstencion durante disable y de que la fuente desaparece despues del delete.
- Video o captura del microfono, transcripcion y audio de `/call`.
- Eventos de escucha y respuesta de `/health`, sin transcript clinico en los eventos.
- Resumen final y alerta persistida.
- Logs y respuesta de `/api/metrics`, sin secretos.

No declarar una compuerta aprobada solo porque el recorrido esta escrito. La matriz de estado
esta en [metricas y evidencia](04_metricas_y_evidencia.md).

El recorrido semantico adicional (benchmark, version de indice, backend, latencias y rollback)
esta especificado en `specs/15_*`, `specs/17_*` y `specs/18_*`; permanece pendiente hasta que
exista runtime y evidencia fechada.

## Rollout y rollback del conocimiento

Antes de promover una variante se valida su manifest, se ejecuta el benchmark y se comprueba la
reconciliación en modo lectura. La promoción registra actor, versión anterior/nueva, commit y
razón. Ante una cita inválida, revisión obsoleta, fuga de documento disabled/deleted o degradación
de latencia, se vuelve al índice anterior o a FTS5 sin borrar el candidato ni reiniciar llamadas
activas:

```text
python -m scripts.validate_rag_index --index-version <version> --strict
python -m scripts.promote_rag_index --index-version <previous-version> --rollback --reason <incident-code>
python -m scripts.rag_status --json --redact-secrets
```

Estas operaciones no sustituyen la prueba manual G4/G5 ni autorizan un despliegue público.

## Estado de las compuertas

- G2: `MANUAL_PENDING` de cronometraje desde entorno limpio.
- G4: `MANUAL_PENDING` de smoke manual con microfono, transcripcion y audio.
- G5: prueba automatizada e integracion local verificadas; `MANUAL_PENDING` de evidencia con el
  documento externo en una demo.
