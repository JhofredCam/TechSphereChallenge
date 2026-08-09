# Spec: Previsualizacion y publicacion de documentos en `/admin`

**Estado:** implementada en runtime; G5 manual pendiente
**Version:** 0.2.0
**Fecha:** 2026-08-08

## Objetivo

Extender la consola `/admin` para que un administrador pueda inspeccionar el texto extraido,
habilitar o deshabilitar un documento sin eliminarlo y conservar la eliminacion permanente como
accion independiente. El agente debe usar unicamente documentos tecnicamente disponibles y
administrativamente habilitados.

La previsualizacion es para inspeccion humana. No crea una nueva fuente RAG, no modifica el
contenido extraido y no debe ejecutar HTML, Markdown ni instrucciones encontradas en el archivo.

## Tech Stack

Se conserva FastAPI/Uvicorn, SQLite con FTS5, PyMuPDF, HTML/CSS/JavaScript sin bundler y los
servicios actuales de documentos/RAG. La ampliacion debe evitar una dependencia nueva para
preview o un segundo indice; `pages.text` y FTS5 siguen siendo las fuentes locales.

## Project Structure

- `app/main.py`: rutas actuales y rutas nuevas de preview/toggle.
- `app/services/documents.py`: estados, `enabled`, revision y delete.
- `app/services/ingestion.py`: extraccion por pagina y chunks.
- `app/services/rag.py`: filtro `status='available' AND enabled=1`.
- `app/web/admin.html` y `app/web/app.js`: tabla, badges, panel y confirmaciones.
- `app/database.py`: migracion, indice, auditoria y snapshot historico.
- `tests/`: migracion, API, preview, RAG y recorrido de conocimiento vivo.

Estas rutas son las propietarias de la implementacion aplicada en este checkout. `app/config.py`
tambien rechaza un limite de upload superior a 25 MB para conservar el limite de seguridad.

## Estado de implementacion

- `enabled`, snapshots de `sources`, conteos y version de esquema migran de forma idempotente
  antes de servir la aplicacion.
- Upload disponible publica de inmediato; un upload duplicado conserva el estado de publicacion
  existente.
- Preview por pagina lee `pages.text`, limita cada respuesta a 8.000 caracteres y mantiene el
  contenido como texto no ejecutable en API y UI.
- `PATCH` cambia solo la publicacion de documentos `available`; el cambio efectivo incrementa
  una vez `corpus_revision` y el no-op no la modifica.
- Delete limpia paginas, chunks, FTS5 y archivo despues del commit; las fuentes conservan una
  instantanea minima y nunca se usan como evidencia RAG nueva.
- Pruebas automatizadas locales: `tests/test_admin_lifecycle.py` (7), regresion API/live (8),
  base/ingestion (9) y suite completa (45). La evidencia manual externa de G5 permanece
  pendiente y no se considera aprobada por estos tests.

| Criterio | Estado de este checkout |
|---|---|
| ADM-AC-01 a ADM-AC-09 | Implementados y cubiertos por pruebas automatizadas locales |
| ADM-AC-10 | Implementacion local probada; evidencia manual G5 externa pendiente |
| ADM-AC-11 y ADM-AC-12 | Implementados y cubiertos por migracion/API/pruebas de lifecycle |

## Code Style

Los contratos separan `status`, `enabled` y `rag_eligible`; no se reutiliza un string de estado
para tres conceptos. Las respuestas JSON usan nombres estables en `snake_case`, errores con
`error_code` y preview como texto para insertar con `textContent`, nunca como HTML ejecutable.

## Contrato actual que se conserva

- Formatos: `.pdf`, `.txt` y `.md`.
- Identidad: SHA-256 de los bytes originales.
- Procesamiento: sincronico durante el upload.
- Estados tecnicos: `processing`, `available`, `needs_ocr` y `error`.
- Persistencia: SQLite, paginas, chunks y FTS5.
- Revision: `corpus_revision`.
- RAG implementado: consulta documentos `available` con `enabled=1`.
- Delete: elimina paginas, chunks y filas FTS5 sin reiniciar.
- G5: upload, uso, delete y olvido sin reinicio.

La ampliacion agrega una bandera `enabled`; no convierte `disabled` en un estado tecnico de
procesamiento:

```text
rag_eligible = status == "available" and enabled == true
```

Una carga nueva empieza `enabled=false` mientras esta `processing` y pasa a `enabled=true` solo
cuando el procesamiento termina en `available`. Esta publicacion inmediata conserva el flujo
actual de G5, pero queda visible para el administrador y es una decision de riesgo que puede
cambiarse a cuarentena antes de implementar.

## Alcance y no objetivos

### Incluye

- Previsualizacion del texto extraido por pagina.
- Distincion visual entre estado tecnico y estado de publicacion.
- Habilitar y deshabilitar sin reprocesar ni eliminar.
- Delete permanente y auditable.
- Revision del corpus y filtro RAG coherentes.
- Pruebas de aprender, olvidar, ocultar y volver a publicar.

### No incluye

- OCR automatico para `needs_ocr`.
- Edicion del contenido original desde `/admin`.
- Autenticacion empresarial o multiusuario.
- Descarga publica de los archivos cargados.
- Renderizado visual completo de PDF como requisito; la preview minima es texto extraido.

## Modelo de estados

| Estado tecnico | `enabled` | Preview | RAG | Acciones permitidas |
|---|---:|---|---:|---|
| `processing` | false | no disponible | no | eliminar |
| `available` | true | texto por pagina | si | preview, deshabilitar, eliminar |
| `available` | false | texto por pagina | no | preview, habilitar, eliminar |
| `needs_ocr` | false | metadatos y aviso | no | eliminar |
| `error` | false | error actual, sin texto viejo | no | eliminar |
| eliminado | no existe | 404 | no | auditoria historica |

`available` significa que existe texto extraible; no significa que el documento este publicado
en el corpus activo.

## Migracion persistida propuesta

La tabla `documents` debe agregar una bandera separada del estado tecnico:

```sql
ALTER TABLE documents ADD COLUMN enabled INTEGER NOT NULL DEFAULT 0
  CHECK (enabled IN (0, 1));
CREATE INDEX IF NOT EXISTS idx_documents_rag_eligibility
  ON documents(status, enabled);
```

La migracion debe ser idempotente y ejecutarse antes de servir consultas. Debe inspeccionar
`PRAGMA table_info(documents)` o el versionado de esquema antes de ejecutar el `ALTER TABLE`;
si `enabled` ya existe, no debe repetirlo. En una base existente, el backfill debe dejar
`enabled=1` solo para documentos `status='available'` y `enabled=0` para `processing`,
`needs_ocr` y `error`. Una carga nueva usa `0` durante procesamiento y cambia a `1` en la misma
transaccion que publica un documento `available`. La migracion debe conservar SHA-256, paginas,
chunks, FTS5 y `corpus_revision`, registrar la version de esquema en `meta` y ser segura ante
una segunda ejecucion.

No se permite una consulta RAG durante el intervalo entre agregar la columna y completar el
backfill. Una migracion fallida bloquea el arranque y no sirve la aplicacion con un esquema
parcial.

## API propuesta

| Metodo y ruta | Contrato | Estado |
|---|---|---|
| `GET /api/admin/documents` | conserva respuesta y agrega `enabled`, `rag_eligible`, `page_count`, `chunk_count` y `preview_available` | ampliar |
| `POST /api/admin/documents` | conserva upload y procesamiento sincronico; nueva carga habilitada | conservar |
| `GET /api/admin/documents/{id}/preview?page=1&offset=0&limit=8000` | devuelve texto extraido seguro y metadatos | nuevo |
| `PATCH /api/admin/documents/{id}` | recibe `{ "enabled": true|false }` | nuevo |
| `DELETE /api/admin/documents/{id}` | elimina contenido indexado y original almacenado | conservar |

### Listado

Cada fila debe exponer al menos:

```json
{
  "id": "sha256",
  "filename": "guia.txt",
  "status": "available",
  "enabled": false,
  "rag_eligible": false,
  "available": true,
  "needs_ocr": false,
  "preview_available": true,
  "page_count": 1,
  "chunk_count": 2,
  "corpus_revision": 7
}
```

Los campos `available` y `needs_ocr` existentes se conservan; la UI nueva debe usar
`rag_eligible` para comunicar si el agente puede recuperar el documento.

### Preview

La respuesta de preview debe incluir `document_id`, `filename`, estado tecnico, `enabled`,
pagina, total de paginas, offset, limite, total de caracteres, truncamiento y texto. Debe:

- leer desde `pages.text`, sin reprocesar el archivo;
- aceptar limites de caracteres con maximo de 8.000 por respuesta;
- conservar saltos de linea;
- tratar TXT y MD como pagina 1;
- mostrar Markdown como texto no ejecutable;
- indicar que en PDF se muestra texto extraido, no una imagen exacta;
- no incrementar `corpus_revision`;
- no devolver `stored_path`;
- devolver `preview.available=false` y `reason=needs_ocr` si no existe capa de texto.

Una preview de `error` no puede mostrar paginas residuales de un procesamiento anterior. Para
garantizarlo, el reprocesamiento debe construir paginas/chunks en una transaccion temporal y,
si falla, eliminar cualquier contenido anterior antes de marcar `error`; el contenido viejo no
puede quedar elegible ni visible por preview. Si un documento `available` pasa a `needs_ocr` o
`error`, se fuerza `enabled=0` y se elimina el indice anterior en la misma transaccion.

Respuesta minima:

```json
{
  "document_id": "sha256",
  "filename": "guia.pdf",
  "status": "available",
  "enabled": true,
  "preview": {
    "available": true,
    "page": 1,
    "page_count": 4,
    "offset": 0,
    "limit": 8000,
    "total_chars": 5230,
    "truncated": false,
    "text": "Texto extraido..."
  },
  "corpus_revision": 7
}
```

`offset` y `limit` son caracteres UTF-8 logicos de la pagina extraida, no bytes ni chunks RAG.
Valores no enteros, negativos, `limit=0` o `limit>8000` responden `422`; pagina fuera de rango
responde `404`; `offset` mayor que `total_chars` responde `422 offset_out_of_range`; documento inexistente responde `404`; `processing` responde `409`; `needs_ocr`
responde `200` con `preview.available=false` y razon explicita.

### Habilitar y deshabilitar

`PATCH` recibe un booleano obligatorio. Solo un documento `available` puede pasar de habilitado
a deshabilitado o viceversa. El cambio debe ser idempotente:

- cambio efectivo: incrementa `corpus_revision` una vez y registra auditoria;
- operacion sin cambio: no incrementa la revision y puede devolver `changed=false`;
- `processing`, `needs_ocr` y `error`: responden `409 document_not_searchable` al intentar
  habilitar;
- deshabilitar conserva archivo, paginas, chunks y FTS5;
- habilitar reutiliza esos datos sin reingesta;
- un upload duplicado por SHA-256 no reactiva un documento deshabilitado.

Respuestas del toggle:

| Caso | HTTP | Respuesta minima |
|---|---:|---|
| cambio efectivo | 200 | documento, `enabled`, `rag_eligible`, `changed=true`, `corpus_revision` |
| operacion sin cambio | 200 | `changed=false`, estado efectivo y misma revision |
| documento inexistente | 404 | `error_code=document_not_found` |
| estado `processing`, `needs_ocr` o `error` | 409 | `error_code=document_not_searchable` |
| JSON sin booleano o con campos desconocidos | 422 | `error_code=invalid_publication_state` |

### Delete

Delete sigue siendo una accion distinta de deshabilitar:

1. Elimina en una transaccion paginas, chunks, filas FTS5 y documento.
2. Incrementa `corpus_revision`.
3. Conserva una instantanea historica minima de las fuentes de llamadas cerradas
   (`filename`, hash, pagina, indice de chunk, cita, score y `corpus_revision`) sin depender de
   una FK a un documento que ya no existe. Esa instantanea no se reutiliza como evidencia nueva.
4. Elimina el archivo de `data/uploads/` despues de confirmar la transaccion.
5. Registra un error de limpieza fisica si no puede eliminar el archivo.
6. Devuelve `404 document_not_found` en un segundo delete.

### Snapshot historico de fuentes

Antes de eliminar una fila referenciada, `sources` debe conservar campos inmutables sin FK:

```text
document_filename_snapshot
document_sha256_snapshot
page_number
chunk_index_snapshot
citation
score
corpus_revision
```

La migracion puede mapearlos desde las columnas actuales o crear las columnas snapshot; no se
requiere conservar el texto completo del documento. Un delete de un documento con llamadas
activas debe permitir terminar el turno con la revision que ya fue leida, pero todo turno nuevo
debe usar la revision posterior y no la snapshot historica.

## UI requerida

La tabla de `/admin` debe mostrar en badges separados:

- procesamiento: Disponible, Necesita OCR, Procesando o Error;
- publicacion: Habilitado, Deshabilitado o No disponible;
- pagina/chunks, tipo de archivo, tamano y fechas en formato comprensible.

La identidad SHA-256 y la revision del corpus siguen siendo contratos internos de API,
persistencia, deduplicacion, auditoria y RAG; no se muestran en la interfaz administrativa.

Acciones:

- **Previsualizar:** abre panel lateral en escritorio y vista completa en movil;
- **Habilitar/Deshabilitar:** confirma el cambio y refresca fila, contadores y revision;
- **Eliminar:** confirmacion explicita, texto irreversible y retirada de la fila.

El contenido de preview se inserta como texto, nunca con `innerHTML`. Un documento
deshabilitado permanece visible y previsualizable. Un documento `needs_ocr` muestra el motivo y
no ofrece habilitar.

### Mejora UX derivada: inventario sin espacio desperdiciado

La propuesta [`08_admin_inventory_ux_specification.md`](08_admin_inventory_ux_specification.md)
define un fix de presentacion separado del ciclo documental. Cuando el preview esta cerrado, el
inventario debe ocupar todo el ancho util; cuando esta abierto, puede compartir el espacio con el
preview. La propuesta elimina por completo el SHA visible, pero conserva la identidad SHA-256 en
API, persistencia, deduplicacion y acciones internas. No cambia `status`, `enabled`,
`rag_eligible`, revision, snapshots ni el filtro RAG.

La implementacion local de la propuesta queda `IMPLEMENTED` en `app/web/`: el layout cerrado usa
una sola columna, el preview abierto agrega una segunda zona y el inventario se transforma en
fichas sin scroll horizontal en viewports estrechos. Los estados de procesamiento y publicacion
se presentan por separado, las fechas se localizan y los errores de API se convierten en mensajes
orientados al administrador sin filtrar codigos internos. La inspeccion manual de navegador y
lector de pantalla sigue pendiente. La
previsualizacion del archivo original pertenece a la spec 09 y no se considera incluida en este
fix.

## Invariantes de RAG y concurrencia

1. Toda consulta RAG aplica `status='available' AND enabled=1` en la misma consulta que lee los
   chunks.
2. Nadie consulta `chunks_fts` sin el filtro de elegibilidad.
3. Una pregunta cuya unica evidencia esta deshabilitada retorna abstencion y `sources=[]`.
4. Rehabilitar vuelve a permitir recuperacion sin reprocesar.
5. Delete retira el contenido indexable, no solo la fila visual.
6. Cada fuente nueva conserva documento, pagina, chunk, cita, score y `corpus_revision`; al
   borrar, las referencias FK pueden quedar nulas, pero la instantanea historica minima no se
   pierde.
7. La preview no es contexto clinico para el agente.
8. Las fuentes historicas no se reutilizan en turnos posteriores.
9. Si el corpus cambia mientras se prepara una respuesta, el turno debe revalidar la revision
   antes de persistir la cita; la alternativa segura es abstenerse.
10. Un turno iniciado despues del commit de disable o delete observa la nueva revision.

## Seguridad y limites

- Mantener el maximo de 25 MB y validar extension, bytes y rutas.
- `APP_MAX_UPLOAD_BYTES` no puede superar 25 MB en este alcance; un valor mayor se rechaza al
  arrancar o se limita con error visible, nunca se aplica silenciosamente.
- Derivar almacenamiento del hash y no aceptar rutas del cliente.
- Escapar preview y delimitarla como contenido no confiable.
- No exponer claves, rutas internas ni contenido completo por defecto.
- Mantener el admin local en `127.0.0.1` mientras no exista autenticacion.
- El servidor debe rechazar o advertir explicitamente un bind fuera de `127.0.0.1` mientras no
  exista autenticacion; la prueba de despliegue debe comprobar la URL efectiva.
- Si se expone fuera de localhost, detener la implementacion y pedir autenticacion,
  autorizacion, CSRF, rate limiting y revision de privacidad.
- No usar el toggle para ocultar una alerta clinica ya persistida; solo controla nuevas
  recuperaciones del conocimiento.

## Comandos de verificacion ejecutados

Desde la raiz se ejecutaron los siguientes comandos durante la implementacion:

```text
python -m pytest tests/test_api.py tests/test_live_knowledge.py -q
python -m pytest tests/test_database.py tests/test_ingestion.py -q
python -m pytest -q --basetemp <temp>
ruff check .
```

Resultado local: `7`, `8`, `9` y `45` pruebas pasaron respectivamente; `ruff check app tests`
no reporto hallazgos. La evidencia manual debe recorrer `/admin` y `/call` con un documento
externo al corpus.

## Estrategia de pruebas

- **Migracion:** `enabled` por defecto segun estado tecnico, indice de elegibilidad, backfill e
  idempotencia contra una base preexistente; una migracion fallida no arranca el servidor.
- **Servicio:** upload nuevo, duplicado, toggle efectivo y no-op, delete en ambos estados.
- **Preview:** PDF/TXT/MD, paginas, truncamiento, HTML, prompt injection, OCR, error y 404.
- **RAG:** aparece habilitado, desaparece deshabilitado, reaparece habilitado y se olvida al
  borrar sin reiniciar.
- **API:** contratos existentes, `PATCH`, `404`, `409`, `413`, `415` y `422`.
- **Preview:** offset fuera de rango, limite maximo y documentos `needs_ocr` deben devolver el
  codigo estable documentado.
- **UI:** badges separados, preview segura y diferencia inequívoca entre deshabilitar y borrar.
- **Manual:** upload, preview, consulta grounded, disable, abstencion, enable, recuperacion,
  delete y abstencion final.

## Limites

- **Siempre:** separar `status` de `enabled`, filtrar RAG por `rag_eligible`, preservar citas
  historicas, validar contenido no confiable y mantener delete disponible.
- **Preguntar antes:** cambiar el esquema persistido, introducir autenticacion, agregar OCR,
  renderizar PDF visual, cambiar la politica de cuarentena o exponer el admin publicamente.
- **Nunca:** presentar un documento deshabilitado como activo, borrar silenciosamente al
  deshabilitar, ejecutar contenido de preview, usar una cita historica como evidencia nueva o
  declarar G5 verificado solo por la UI.

## Criterios de exito

- **ADM-AC-01:** el listado conserva el contrato actual y muestra `enabled` y `rag_eligible`.
- **ADM-AC-02:** PDF, TXT y MD disponibles pueden previsualizarse por pagina sin ejecutar su
  contenido.
- **ADM-AC-03:** `needs_ocr` muestra advertencia y nunca participa en RAG.
- **ADM-AC-04:** deshabilitar conserva el documento y lo excluye de consultas nuevas.
- **ADM-AC-05:** habilitar recupera el documento sin reingesta.
- **ADM-AC-06:** toggle efectivo incrementa una sola vez `corpus_revision`; el no-op no lo hace.
- **ADM-AC-07:** delete mantiene su contrato, limpia FTS5 y hace que consultas nuevas olviden
  la fuente sin reiniciar.
- **ADM-AC-08:** la UI distingue preview, habilitar, deshabilitar y eliminar.
- **ADM-AC-09:** las pruebas cubren concurrencia de revision, duplicados y estados no publicables.
- **ADM-AC-10:** G5 conserva un recorrido con material externo al corpus.
- **ADM-AC-11:** una base existente migra de forma idempotente y solo publica documentos
  `available`.
- **ADM-AC-12:** preview, toggle y delete devuelven contratos `200/404/409/422` definidos y
  nunca exponen `stored_path`.

## Dependencias y preguntas abiertas

- Depende de `specs/03_mvp_structure_specification.md` para ownership de artefactos.
- `specs/06_system_flow_diagram_specification.md` debe ser actualizado por su agente propietario
  despues de este cambio; no se modifica como parte de esta implementacion.
- Debe mantener coherencia con G5, README, `docs/arquitectura.md` y evidencia.

Preguntas abiertas:

1. La carga nueva queda habilitada cuando termina `available`, conforme a la decision vigente;
   una cuarentena previa queda como alternativa futura, no como comportamiento actual.
2. La preview minima de texto extraido es suficiente para este corte; el render visual de PDF
   sigue fuera de alcance.
3. Sigue abierta la decision de exigir una razon obligatoria por toggle y la retencion detallada
   de auditoria.
4. La politica de cancelacion para turnos que coincidan con una mutacion de corpus debe
   integrarse con la revalidacion del flujo de llamadas posterior.
5. Se requiere autenticacion, CSRF y controles de exposicion antes de cualquier despliegue fuera
   de localhost.
