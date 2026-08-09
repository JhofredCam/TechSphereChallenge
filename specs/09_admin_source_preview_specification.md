# Spec: Previsualizacion del archivo original en `/admin`

**ID:** `ADMIN-SOURCE-PREVIEW-001`
**Estado:** `PROPOSED`; no implementada en este checkout
**Version:** 0.1.0
**Fecha:** 2026-08-08
**Propietario:** consola `/admin`
**Depende de:** [`04_admin_document_lifecycle_specification.md`](04_admin_document_lifecycle_specification.md)
**Complementa:** [`08_admin_inventory_ux_specification.md`](08_admin_inventory_ux_specification.md)

## Objetivo

Permitir que el administrador abra una ventana emergente accesible y compruebe como era el
archivo que originalmente subio. La experiencia debe distinguir sin ambiguedad entre:

1. **Archivo original:** la representacion del PDF, TXT o MD tal como fue recibido y almacenado.
2. **Texto extraido:** el resultado de la ingestion que actualmente usa la preview por pagina.

La funcionalidad sirve para validar visualmente el origen de una fuente, identificar si una
pagina fue escaneada y entender por que el texto indexado puede diferir del archivo. No crea una
nueva fuente RAG, no reingesta, no modifica el documento y no convierte el contenido subido en
HTML ejecutable.

## Supuestos explicitos

1. El original ya se conserva en `stored_path` derivado del SHA-256; no se crea una segunda copia
   ni se expone la ruta fisica al navegador.
2. La superficie continua limitada a localhost mientras no exista autenticacion, CSRF y control
   de permisos.
3. Un PDF puede mostrarse mediante el visor seguro del navegador; esta eleccion permite conservar
   paginas, imagenes y disposicion, pero no promete impedir que una persona con acceso al navegador
   guarde una copia.
4. TXT y MD se muestran como texto plano literal, incluso si contienen HTML, Markdown o texto que
   intenta cambiar las instrucciones del agente.
5. `status`, `enabled` y `rag_eligible` mantienen la semantica de la Spec 04. Ver el original no
   habilita el documento.
6. La API nueva, si se aprueba, sera de lectura y no incrementara `corpus_revision`.

## Tech Stack

- FastAPI/Uvicorn para un endpoint de lectura binaria seguro.
- HTML semantico con `dialog` nativo o equivalente accesible.
- CSS sin bundler para overlay, pestañas, visor y responsive.
- JavaScript existente en `app/web/app.js`, sin dependencias de renderizado Markdown.
- PyMuPDF e ingestion actuales solo para el texto extraido y el estado OCR.
- SQLite conserva metadatos; el archivo original se sirve desde la ruta privada validada por el
  servicio documental.

No se agrega una libreria PDF obligatoria en este corte. El visor nativo del navegador es el
primer camino; una biblioteca local solo puede proponerse despues de evaluar tamano, licencia,
seguridad y setup de 15 minutos.

## Project Structure futuro

```text
app/main.py                    -> endpoint de lectura del original y headers
app/schemas.py                 -> metadatos de formato y disponibilidad, si son necesarios
app/services/documents.py      -> resolucion segura de la ruta almacenada
app/services/ingestion.py      -> formato canonico y estado needs_ocr
app/web/admin.html             -> dialog, pestañas y contenido alternativo
app/web/app.js                 -> abrir/cerrar, foco, carga y estados obsoletos
app/web/styles.css             -> modal, iframe/pre, responsive y reduced motion
tests/test_admin_lifecycle.py  -> contratos de fuente y regresiones de estados
tests/test_api.py              -> headers, errores y bytes
tests/test_http_contracts.py   -> contrato HTTP sin rutas internas
specs/04_*                     -> ciclo documental y preview extraido
specs/06_*                     -> trazabilidad de archivo original y RAG
specs/07_*                     -> automatizacion y smoke manual
```

Esta spec no crea esos archivos ni modifica el runtime; define el contrato previo a la
implementacion.

## Experiencia funcional

### Abrir la ventana

Cada fila o ficha de documento disponible para inspeccion debe tener un boton:

```text
Previsualizar "guia de alta.pdf"
```

El nombre es contextual y no contiene SHA, `document_id`, ruta fisica ni codigo tecnico. Al
activar el boton:

1. se guarda la referencia al boton invocador;
2. se abre la ventana con el titulo del archivo;
3. se selecciona por defecto **Archivo original**;
4. se muestra un indicador de carga que no bloquea la lectura del titulo;
5. el foco entra en el boton de cierre o en el titulo, segun la implementacion accesible;
6. se solicita el original usando el identificador completo internamente;
7. se muestra una alternativa textual si el visor no puede abrir el formato.

Cerrar con `Esc`, el boton `Cerrar` o el control de cierre debe:

- cancelar o ignorar una solicitud pendiente;
- retirar el contenido anterior para no mostrar una respuesta obsoleta al abrir otro documento;
- devolver el foco al boton invocador;
- no modificar auditoria, revision, paginas, chunks, FTS5 o estado de publicacion.

### Pestañas o modos

La ventana debe tener dos controles de modo claramente rotulados:

| Modo | Que muestra | Fuente | Puede entrar al RAG |
|---|---|---|---|
| Archivo original | formato visual/literal recibido | bytes originales almacenados | No |
| Texto extraido | texto por pagina y limites existentes | `pages.text` | No por el hecho de verlo |

El texto de ayuda obligatorio es:

- `Archivo original: asi fue recibido. No es el texto indexado.`
- `Texto extraido: resultado de la ingestion. Puede diferir del archivo visual.`

El modo seleccionado debe anunciarse a lectores de pantalla con `aria-selected` o un mecanismo
equivalente. No se debe diferenciar solo por color.

## Representacion por formato

### PDF

- Servir el original con `Content-Type: application/pdf` canonico.
- Usar `Content-Disposition: inline` y un visor embebido con `title` descriptivo.
- Aislar el visor con `sandbox` sin scripts, formularios ni navegacion superior cuando el
  navegador lo permita.
- Mantener zoom, paginas e imagenes del archivo original.
- Ofrecer una alternativa visible: `Si el visor no abre el PDF, revisa el texto extraido o abre
  el archivo con un lector PDF local.`
- No asumir que PDF visual implica capa de texto.
- Un PDF `needs_ocr` puede tener modo original disponible y modo texto extraido no disponible.
- Un PDF mixto puede mostrarse completo; el estado de texto debe explicar que alguna pagina puede
  no tener texto extraible.

El visor PDF del navegador puede permitir guardar, imprimir o copiar. La documentacion debe
declararlo de forma honesta; `inline`, `no-store` y `X-Frame-Options` reducen exposicion de red,
pero no pueden impedir una copia hecha por una persona con acceso al navegador.

### TXT

- Servir como `text/plain; charset=utf-8`.
- Mostrar exactamente saltos de linea y caracteres validos.
- Insertar el contenido con `textContent` o un nodo equivalente.
- No interpretar etiquetas, estilos, enlaces, scripts ni instrucciones.
- Permitir seleccion y desplazamiento vertical dentro de la ventana.

### MD

- Servir como `text/plain; charset=utf-8` en la vista de origen.
- Mostrar los marcadores Markdown literalmente, incluidos `#`, `*`, backticks y enlaces.
- No convertir Markdown a HTML.
- No ejecutar HTML embebido ni enlaces con esquema `javascript:`.
- La pestaña de texto extraido conserva el comportamiento seguro ya definido por la Spec 04.

## Contrato HTTP propuesto

### Endpoint del original

```text
GET /api/admin/documents/{document_id}/source
```

El endpoint recibe el identificador completo en la URL, resuelve el registro en la base y solo
sirve un archivo cuya ruta:

1. proviene del registro, nunca de una ruta enviada por el cliente;
2. esta dentro del directorio configurado de uploads;
3. corresponde al SHA y al nombre seguro del documento;
4. existe y es legible;
5. tiene un formato soportado por la politica del servidor.

El endpoint no recibe `path`, `filename` ni una URL externa como parametro.

### Respuesta exitosa

| Formato | Content-Type | Disposicion |
|---|---|---|
| PDF | `application/pdf` | `inline` |
| TXT | `text/plain; charset=utf-8` | `inline` |
| MD | `text/plain; charset=utf-8` | `inline` |

Headers minimos:

```text
X-Content-Type-Options: nosniff
Cache-Control: no-store
Referrer-Policy: no-referrer
Content-Disposition: inline; filename*=UTF-8''<nombre-saneado>
```

`X-Frame-Options: SAMEORIGIN` o una politica CSP equivalente debe ser compatible con el visor
embebido. No se acepta un MIME tomado directamente de `UploadFile.content_type`; el servidor debe
usar una tabla canonica por extension/formato validado.

El nombre de `Content-Disposition` se sanea y no puede contener salto de linea, comillas sin
escapar, ruta, control characters ni un nombre enviado para escapar del directorio.

### Metadatos del listado

La UI puede necesitar estos campos aditivos, sin exponer rutas:

```json
{
  "source_format": "pdf",
  "source_media_type": "application/pdf",
  "original_preview_available": true,
  "preview_available": false,
  "status": "needs_ocr"
}
```

`preview_available` significa texto extraido. `original_preview_available` significa que el
archivo original puede leerse desde la ruta controlada. No se deben añadir `stored_path`, URL de
filesystem, bytes ni secretos al JSON.

### Errores

| Caso | HTTP | `error_code` | Mensaje de interfaz |
|---|---:|---|---|
| Documento inexistente | 404 | `document_not_found` | `No encontramos esta fuente.` |
| Procesamiento en curso | 409 | `document_processing` | `La fuente aun se esta procesando.` |
| Documento en error sin fuente valida | 409 | `source_unavailable` | `El archivo original no esta disponible.` |
| Ruta ausente o fuera de raiz | 409 | `source_unavailable` | `No pudimos abrir el archivo original.` |
| Formato no permitido | 415 | `source_format_not_supported` | `Este formato no se puede previsualizar aqui.` |
| Fallo de lectura | 503 | `source_read_error` | `No pudimos abrir esta fuente. Intentalo de nuevo.` |

Los mensajes al cliente no contienen rutas, stack traces, MIME recibido, excepciones, hashes ni
detalles de almacenamiento. Los logs internos pueden registrar el incidente con la politica de
privacidad vigente.

### Texto extraido existente

`GET /api/admin/documents/{id}/preview` no cambia. Debe conservar:

- pagina, offset, limite y total de caracteres;
- limite maximo de 8.000 caracteres;
- `preview.available` y `reason=needs_ocr`;
- texto literal y no ejecutable;
- `404`, `409` y `422` existentes;
- ausencia de `stored_path`;
- no incremento de `corpus_revision`.

La nueva vista original no debe reutilizar ni alterar este endpoint para devolver bytes.

## Estados y reglas de negocio

| Estado documental | Archivo original | Texto extraido | Publicacion RAG |
|---|---|---|---|
| `processing` | 409 mientras no finalice | 409 o estado existente | no |
| `available + enabled=true` | disponible | disponible | si |
| `available + enabled=false` | disponible | disponible | no |
| `needs_ocr` | disponible si el archivo se puede leer | aviso, no texto utilizable | no |
| `error` | solo si el original valido persiste | no mostrar paginas antiguas | no |
| eliminado | 404 | 404 | no |

Ver el original o el texto extraido nunca cambia `enabled`. Un documento deshabilitado continua
siendo inspeccionable por el administrador, pero no aparece en consultas nuevas del RAG.

Si el documento se elimina con la ventana abierta:

- una nueva solicitud devuelve 404;
- la ventana muestra `Esta fuente fue eliminada y ya no esta disponible.`;
- no se reutiliza una respuesta pendiente como contenido de otro documento;
- el snapshot de llamadas cerradas sigue siendo historico y no se expone como archivo original.

## Seguridad

### Frontera de confianza

El archivo subido y su contenido son datos no confiables. La previsualizacion no debe ejecutar,
interpretar ni enviar al modelo:

- HTML, JavaScript, SVG activo o formularios;
- instrucciones de prompt injection;
- enlaces externos;
- macros o contenido activo de un PDF;
- metadatos tecnicos internos.

TXT y MD siempre son texto plano. El PDF debe aislarse en un contexto de visor restringido, sin
pretender que `sandbox` elimina todos los riesgos del parser del navegador.

### Validacion del servidor

- validar extension, firma y lectura del PDF antes de ofrecerlo como visor PDF;
- ignorar MIME declarado por el cliente al construir la respuesta;
- comprobar que el path resuelto no escapa del directorio de uploads;
- rechazar symlinks o enlaces que permitan escapar de la raiz configurada;
- usar identificadores parametrizados y no concatenar rutas desde input;
- limitar tamano, numero de solicitudes y tiempo de lectura conforme a la politica local;
- no cachear el original por defecto;
- no publicar la ruta fuera de localhost sin autenticacion y autorizacion.

### Privacidad

El catalogo puede mostrar nombre, formato y fecha, pero nunca rutas fisicas, secretos, tokens,
contenido de eventos ni texto de pacientes fuera del archivo que el administrador eligio ver.
Debe quedar claro en la ventana:

```text
Vista administrativa local. El archivo original puede ser guardado por el navegador.
```

## Accesibilidad y responsive

- preferir `dialog` nativo con `aria-modal="true"`, `aria-labelledby` y `aria-describedby`;
- si el soporte exige un dialog propio, implementar focus trap, Escape y restauracion de foco;
- titulo dinamico: `Previsualizacion de <nombre>` sin SHA;
- botones `Archivo original`, `Texto extraido` y `Cerrar` con estado seleccionado anunciable;
- `<iframe>` PDF con `title` descriptivo y alternativa textual visible;
- `<pre>` de TXT/MD con lectura por teclado y wrap de linea configurable;
- en movil, ventana casi completa con scroll interno vertical;
- en escritorio, ancho maximo legible y altura limitada al viewport;
- soportar zoom 200 %, contraste y `prefers-reduced-motion`;
- no depender del color para diferenciar modos o estados;
- no permitir que el contenido del archivo rompa el titulo, botones o foco del dialog.

## Code Style de referencia

El contrato de rendering debe mantener los datos como datos:

```text
sourceFrame.src = `/api/admin/documents/${encodeURIComponent(documentId)}/source`
sourceText.textContent = originalText
previewTitle.textContent = `Previsualizacion de ${filename}`
```

La ilustracion no prescribe implementacion concreta. Prohibe formar HTML con el contenido del
archivo, aceptar una ruta del cliente o convertir un nombre no saneado en una URL sin codificar.

## Estrategia de pruebas

### Backend

Agregar pruebas de contrato para:

1. PDF subido: bytes servidos iguales a los bytes originales y MIME canonico.
2. TXT y MD: respuesta literal, `text/plain` aunque el archivo contenga `<script>` o HTML.
3. MIME de upload falso: el servidor no responde con `text/html` ni ejecuta el contenido.
4. PDF corrupto, vacio y PDF escaneado: estados correctos y mensajes seguros.
5. PDF mixto: el original puede verse y el texto extraido informa sus limites.
6. documento `available` deshabilitado: original visible, RAG excluido.
7. documento `processing`, `error` y eliminado: `409/404` correctos sin contenido residual.
8. path traversal, symlink, ruta ausente y nombre con saltos de linea: rechazo seguro.
9. headers `nosniff`, `no-store`, `inline` y nombre saneado.
10. abrir la preview no altera `corpus_revision`, auditoria, paginas, chunks ni FTS5.

### Frontend y manual

El checkout no tiene runner browser. Antes de implementar automatizacion, el smoke manual debe
recorrer Chrome y Edge:

1. subir PDF textual, PDF escaneado, TXT y MD;
2. abrir la modal desde cada fila sin ver SHA o ruta;
3. cambiar entre original y texto extraido;
4. comprobar que el PDF conserva apariencia y que TXT/MD no renderizan HTML/Markdown;
5. probar cierre con boton, Escape y click fuera solo si la politica lo permite;
6. verificar foco, lector de pantalla, zoom, teclado y movil;
7. eliminar un documento con la ventana abierta y confirmar cierre/404;
8. comprobar que deshabilitar solo afecta RAG y no la previsualizacion;
9. observar Network y confirmar ausencia de solicitudes externas;
10. confirmar que el navegador puede guardar el PDF y que esa limitacion esta documentada.

### Comandos propuestos

```text
python -m pytest tests/test_admin_lifecycle.py tests/test_api.py tests/test_http_contracts.py tests/test_ingestion.py -q --basetemp <temp>/source-preview
python -m pytest tests/test_live_knowledge.py -q --basetemp <temp>/source-preview-live
ruff check .
node --check app/web/app.js
git diff --check
```

## Criterios de aceptacion

- **ADMIN-SOURCE-AC-01:** el administrador abre una ventana emergente accesible desde una fuente,
  no una navegacion perdida ni una pestaña sin contexto.
- **ADMIN-SOURCE-AC-02:** la ventana distingue por nombre, estado y ayuda entre archivo original
  y texto extraido.
- **ADMIN-SOURCE-AC-03:** el PDF conserva paginas, imagenes y disposicion del archivo original
  cuando el visor del navegador es compatible.
- **ADMIN-SOURCE-AC-04:** TXT y MD se muestran literalmente como texto plano, sin ejecutar HTML,
  JavaScript ni renderizar Markdown.
- **ADMIN-SOURCE-AC-05:** un PDF `needs_ocr` puede visualizarse como archivo original, pero no se
  presenta como texto extraido utilizable ni como documento elegible para RAG.
- **ADMIN-SOURCE-AC-06:** el endpoint original no expone `stored_path`, rutas fisicas, secretos,
  hashes ni MIME controlado por el cliente.
- **ADMIN-SOURCE-AC-07:** abrir, cambiar de pestaña o cerrar no modifica corpus, revision,
  auditoria, paginas, chunks, FTS5 o publicacion.
- **ADMIN-SOURCE-AC-08:** `processing`, `error`, archivo ausente y eliminado tienen estados
  accesibles, errores estables y no muestran contenido obsoleto.
- **ADMIN-SOURCE-AC-09:** el texto extraido conserva todos los contratos de la Spec 04, incluido
  limite 8.000 y `textContent`.
- **ADMIN-SOURCE-AC-10:** foco, teclado, Escape, lector de pantalla, zoom, movil y fallback del
  visor funcionan sin depender del color.
- **ADMIN-SOURCE-AC-11:** el administrador recibe una advertencia honesta de que el visor PDF
  permite guardar o copiar mediante el navegador.
- **ADMIN-SOURCE-AC-12:** la nueva vista no cambia los gates G2, G4 o G5 ni se presenta como
  evidencia de conocimiento vivo por si sola.

## Trazabilidad y sincronizacion

| Requisito | Spec o ruta origen | Reflejo antes de implementar |
|---|---|---|
| Archivo original almacenado | Spec 04, `documents.py` | contrato de resolucion segura |
| Texto extraido por pagina | Spec 04, `GET .../preview` | mantener endpoint actual |
| Estado OCR | `ingestion.py`, Spec 04 | tabla de estados y pruebas |
| Admin full-width y sin SHA visible | Spec 08 | mantener boton y modal sin IDs visibles |
| RAG solo disponible + habilitado | Spec 04, Spec 06 | no alterar filtro |
| Seguridad de contenido | Spec 00, Spec 07 | pruebas de XSS, MIME y path |

Antes de escribir codigo:

1. actualizar la Spec 04 para incluir este endpoint y revisar su no-objetivo de render PDF;
2. actualizar Spec 06 con `API-ADMIN-SOURCE`, `DATA-FILES` y el flujo de preview original;
3. actualizar Spec 07 con pruebas binarias, MIME independiente y smoke modal;
4. actualizar `README.md`, `docs/arquitectura.md` e indice documental;
5. revisar que la Spec 08 siga ocultando SHA y rutas en la UI;
6. implementar solo despues de aprobar el riesgo de visor PDF.

## Limites

- **Siempre:** servir el original desde una ruta resuelta por servidor, validar formato, aislar
  contenido no confiable, diferenciar origen y texto extraido y mantener RAG sin cambios.
- **Preguntar antes:** agregar PDF.js u otra dependencia, rasterizar PDFs, permitir descargas
  explicitas, exponer `/admin` fuera de localhost, persistir blobs nuevos o cambiar el esquema.
- **Nunca:** aceptar una ruta del cliente, servir MIME arbitrario, usar `innerHTML`, convertir MD
  a HTML en esta vista, mostrar rutas/SHA o afirmar que un visor PDF impide copiar el archivo.

## Preguntas abiertas

1. Confirmar si la organizacion acepta la limitacion de que el visor nativo permite guardar el PDF.
2. Confirmar si el modo de texto extraido debe iniciar en la misma pagina que tenia abierta la
   preview actual o siempre en pagina 1.
3. Confirmar si un PDF mixto debe mostrar una insignia por pagina sin agregar OCR automatico.
4. Confirmar si el endpoint binario debe incorporar `ETag`; si se agrega, debe conservar `no-store`
   o documentar la politica de cache con cuidado.
