# Spec: Inventario de fuentes orientado al administrador

**ID:** `ADMIN-UX-001`
**Estado:** `IMPLEMENTED`; contrato estatico local verificado; smoke browser pendiente por runtime no disponible
**Version:** 0.1.0
**Fecha:** 2026-08-08
**Propietario:** consola `/admin`
**Spec relacionada:** [`04_admin_document_lifecycle_specification.md`](04_admin_document_lifecycle_specification.md)

## Objetivo

Corregir la presentacion del inventario de fuentes en `/admin` para que el bloque de texto
"Fuentes cargadas" use todo el ancho horizontal disponible cuando no hay una previsualizacion
abierta. La vista no debe reservar una columna vacia ni obligar al administrador a usar un scroll
horizontal para consultar una fila.

La experiencia debe hablar en terminos comprensibles para una persona administradora. El SHA-256,
el identificador interno y cualquier otro identificador tecnico no son informacion de producto y
no deben aparecer en la interfaz visible. El hash continua siendo la identidad interna necesaria
para API, persistencia, deduplicacion, auditoria y acciones seguras.

### Resultado esperado

- Con el preview cerrado, el inventario ocupa el 100 % del ancho util de su contenedor.
- Con el preview abierto en escritorio, inventario y preview comparten el espacio sin dejar una
  tercera zona vacia.
- En pantallas estrechas, cada documento puede leerse como ficha apilada sin scroll horizontal.
- Nombre, estado, fecha, tamano, paginas, fragmentos y acciones siguen siendo comprensibles.
- El administrador nunca ve el SHA completo, un prefijo del SHA ni un boton para copiarlo.

## Supuestos explicitos

1. La funcionalidad sigue siendo una superficie local de administracion; no se agrega
   autenticacion, multiusuario ni un nuevo endpoint.
2. El preview lateral/modal puede estar cerrado u abierto y su estado es la causa legitima para
   cambiar entre una y dos columnas.
3. Las acciones actuales siguen usando el identificador completo en memoria y en la URL, aunque
   el identificador no se renderice como texto.
4. `status`, `enabled` y `rag_eligible` continuan siendo contratos distintos. La UI traduce sus
   valores a lenguaje humano y no crea un estado tecnico nuevo.
5. "Sin scroll" significa que la pagina y el inventario no necesitan desplazamiento horizontal en
   los viewports soportados; el texto largo puede ocupar varias lineas.
6. Los datos del reto son sinteticos y no validan decisiones clinicas.

## Tech Stack y limites tecnicos

- HTML semantico, CSS sin bundler y JavaScript existente en `app/web/`.
- API actual de documentos en `app/main.py` y contratos de `app/schemas.py`.
- No se agrega una biblioteca de tablas, un framework visual ni una dependencia de navegador.
- No se cambia SQLite, FTS5, ingestion, SHA-256, RAG, OCR ni el contrato de upload.
- No se usa `overflow-x: hidden` sobre `body` como sustituto de un layout correcto.
- No se elimina informacion funcional para ocultar un desbordamiento; se reorganiza su presentacion.

## Situacion actual y causa del fix

El layout actual de `app/web/styles.css` usa un grid con dos columnas dentro de
`.admin-workspace` incluso cuando `#preview-panel` esta oculto. Por eso la tabla de fuentes ocupa
aproximadamente `1.4fr` y queda una columna vacia de `0.6fr`.

La tabla tambien declara `overflow-x: auto`; sus badges y acciones no siempre pueden envolver el
contenido, por lo que aparece un scroll local. El fix debe resolver las dos causas por separado:

1. cambiar el layout segun el estado real del preview;
2. reestructurar las filas para que las celdas puedan envolver o pasar a una ficha responsive.

La fila actual muestra un prefijo de SHA, tamano, revision y fechas. Esta spec elimina el SHA y
los identificadores tecnicos de la vista de cliente; no solicita borrar esos campos del JSON ni de
la base.

## Alcance

### Incluye

- Layout de una columna cuando el preview esta cerrado.
- Layout de dos columnas solo cuando el preview esta abierto y el viewport lo permite.
- Fichas o tabla refluible para viewports estrechos.
- Eliminacion del SHA visible, completo o abreviado.
- Traduccion de estados tecnicos a mensajes orientados al administrador.
- Acciones con nombres contextuales y estados de carga/error accesibles.
- Conservacion de la tabla semantica en escritorio o de una estructura equivalente accesible en
  movil.
- Actualizacion de las specs upstream y de la matriz de verificacion antes de implementar.

### No incluye

- Cambiar el endpoint `GET /api/admin/documents`.
- Cambiar la identidad SHA-256 interna ni el algoritmo de deduplicacion.
- Agregar autenticacion, permisos o auditoria nueva.
- Agregar preview visual del archivo original; eso pertenece a
  [`09_admin_source_preview_specification.md`](09_admin_source_preview_specification.md).
- Cambiar el filtro RAG `status='available' AND enabled=1`.
- Ocultar errores con CSS o convertir scroll horizontal de la pagina en scroll invisible.
- Exponer una pagina tecnica de diagnostico dentro de la vista principal.

## Contenido visible y contenido interno

### Informacion que si debe ver el administrador

| Dato | Presentacion | Regla UX |
|---|---|---|
| Nombre original | titulo de la ficha/fila | completo cuando quepa; elipsis solo con nombre accesible completo |
| Tipo de archivo | etiqueta humana, por ejemplo `PDF` o `Texto` | no depende unicamente del color |
| Estado de procesamiento | badge y texto | `Disponible`, `Procesando`, `Necesita revision` o `Error al procesar` |
| Estado de publicacion | badge y texto | `Disponible para el agente`, `No disponible para el agente` o `No publicable` |
| Paginas y fragmentos | metadatos legibles | por ejemplo, `4 paginas · 18 fragmentos` |
| Tamano | formato humano | KB/MB, sin bytes crudos salvo detalle accesible |
| Fecha | formato local comprensible | no mostrar timestamps ISO como contenido principal |
| Acciones | botones contextuales | preview, habilitar/deshabilitar y eliminar segun estado |
| Explicacion de OCR | ayuda contextual | explicar que falta texto extraible, sin exponer `needs_ocr` como codigo |

### Informacion que no debe aparecer en la vista visible

- SHA-256 completo.
- Prefijo de SHA-256, incluso si se rotula como `SHA abc123`.
- `document_id`, `id` o identificadores internos equivalentes.
- Rutas fisicas como `data/uploads/...` o `stored_path`.
- Consultas SQL, nombres de tablas, nombres de columnas o revision interna del corpus como
  metadato de producto.
- Mensajes de excepcion, stack traces, nombres de proveedores o codigos HTTP.

El API puede seguir devolviendo `id`, `document_id`, `sha256` y `corpus_revision` para que el
cliente ejecute acciones. JavaScript debe conservarlos en el estado de la aplicacion sin
insertarlos en nodos visibles, atributos accesibles, `title`, `aria-label`, tooltips ni logs de
interfaz.

## Comportamiento responsive

### Layout de escritorio

Con el preview cerrado:

```text
+---------------------------------------------------------------+
| Fuentes cargadas                              [Actualizar]    |
| inventario completo, sin columna lateral reservada           |
+---------------------------------------------------------------+
```

Con el preview abierto:

```text
+--------------------------------+------------------------------+
| Inventario                     | Preview                      |
| ancho flexible                 | ancho legible y limitado     |
+--------------------------------+------------------------------+
```

Requisitos:

- el contenedor cerrado usa una sola pista de grid o un equivalente que ocupe `1fr`;
- el segundo panel no debe conservar espacio cuando esta `hidden`;
- el panel abierto puede usar dos pistas, pero debe tener un minimo razonable y nunca empujar al
  viewport fuera de la pantalla;
- nombres y mensajes largos hacen wrap normal;
- las acciones pueden pasar a una segunda linea dentro de la ficha, no ampliar la tabla.

### Layout movil

En anchos aproximados de 320, 375, 540 y 768 px:

- los documentos se muestran como fichas de una columna o como tabla transformada a bloques;
- el nombre, estado y acciones quedan en orden de lectura;
- paginas, fragmentos, tamano y fecha no desaparecen sin una alternativa visible;
- cada accion puede ocupar el ancho de la ficha y tener un objetivo tactil comodo;
- el preview aparece debajo del inventario o como modal de pantalla completa;
- `document.documentElement.scrollWidth` no supera `clientWidth` en condiciones normales;
- no se usa una barra horizontal para leer el contenido primario.

Se permite scroll vertical dentro de la pagina y dentro de un contenido de preview muy largo. El
scroll horizontal no es una estrategia de layout para la tabla.

## Estados de interfaz

| Estado | Procesamiento | Publicacion | Acciones visibles | Mensaje cliente |
|---|---|---|---|---|
| Carga inicial | Cargando fuentes | - | ninguna | `Estamos cargando tus fuentes...` |
| Vacio | - | - | ninguna | `Aun no hay fuentes cargadas.` |
| `available + enabled=true` | Disponible | Disponible para el agente | previsualizar, deshabilitar, eliminar | `El agente puede consultar esta fuente.` |
| `available + enabled=false` | Disponible | No disponible para el agente | previsualizar, habilitar, eliminar | `La fuente se conserva, pero el agente no la consulta.` |
| `processing` | Procesando | No disponible | eliminar, si el contrato actual lo permite | `Estamos procesando esta fuente.` |
| `needs_ocr` | Necesita revision | No publicable | previsualizacion de origen cuando Spec 09 lo permita, eliminar | `No encontramos texto utilizable. Se necesita OCR.` |
| `error` | Error al procesar | No publicable | eliminar | `No pudimos procesar esta fuente.` |
| Mutacion | estado anterior | estado anterior | controles afectados deshabilitados | `Actualizando la fuente...` |
| Error de red | estado desconocido | estado desconocido | reintentar | `No pudimos actualizar la lista. Intentalo de nuevo.` |

Los textos anteriores son copy de referencia. La futura implementacion debe centralizarlos y
mantener consistencia con la Spec 11 de UX Writing; no debe mostrar los codigos internos en lugar
de estos mensajes.

## Contratos que deben conservarse

1. `GET /api/admin/documents` mantiene `{ documents: [...], count: N }`.
2. Las acciones siguen enviando el identificador completo recibido de la API, nunca un nombre ni
   un prefijo visible.
3. `PATCH` recibe unicamente `{ "enabled": true|false }` y conserva su idempotencia.
4. `DELETE` mantiene confirmacion, semantica irreversible y `404 document_not_found` posterior.
5. Preview textual mantiene pagina, offset, limite maximo de 8.000, `textContent` y respuestas
   `404/409/422`, sin crear una nueva fuente RAG.
6. `status`, `enabled`, `rag_eligible`, `available`, `needs_ocr`, conteos y fechas siguen siendo
   datos de contrato, aunque algunos se traduzcan u oculten en la vista principal.
7. Deshabilitar conserva documento, paginas y fragmentos; eliminar retira contenido indexable y
   conserva solo snapshots historicos permitidos.
8. Ningun cambio estetico puede volver a incluir documentos deshabilitados o eliminados en RAG.

## Accesibilidad

- Mantener tabla semantica con `caption`, `thead`, `th scope="col"` y orden de lectura estable, o
  proporcionar una estructura de fichas equivalente con todos los mismos datos.
- No ocultar paginas, fragmentos o estados solo con `display:none` en movil.
- Usar texto y no solo color para procesamiento y publicacion.
- Cada boton debe nombrar el documento de forma humana, por ejemplo `Previsualizar guia de alta`.
  No incluir SHA ni `document_id` en el nombre accesible.
- Mantener `aria-live="polite"` para carga, exito y error sin anunciar cada cambio de layout.
- Conservar foco visible y devolver el foco al boton que abre el preview.
- Asegurar navegacion completa por teclado y objetivos tactiles de al menos 44 px cuando sea
  posible.
- Soportar zoom de 200 % y reflow sin perdida de funciones.
- La eliminacion debe pedir confirmacion con nombre de archivo, no con hash.

## Seguridad y privacidad de interfaz

- El hash completo puede seguir en peticiones internas, pero no en texto, atributos, `data-*`,
  `title`, `aria-*`, clipboard, alertas ni telemetria de UI.
- El nombre de archivo y el contenido extraido son datos no confiables; renderizar con
  `textContent`, no con `innerHTML`.
- No mostrar rutas locales, credenciales, mensajes del proveedor ni trazas.
- No registrar en consola del navegador payloads completos del inventario en produccion/demo.
- No usar el nombre de archivo como identificador de mutacion; dos archivos con el mismo nombre
  pueden tener hashes diferentes.
- La ausencia visual del SHA no elimina la necesidad de autorizar y validar las acciones en el
  servidor si la superficie deja de ser exclusivamente local.

## Project Structure de la futura implementacion

```text
app/web/admin.html   -> estructura semantica del inventario
app/web/styles.css   -> grid cerrado/abierto y layout responsive
app/web/app.js       -> estado, acciones, copy y rendering seguro
app/main.py          -> contratos actuales, sin endpoint nuevo por esta spec
app/services/        -> sin cambios de comportamiento RAG o documental
tests/               -> contratos API existentes y smoke visual/manual
specs/04_*           -> contrato documental upstream
specs/06_*           -> diagrama y matriz de trazabilidad
specs/07_*           -> estrategia de pruebas y evidencia
```

## Code Style de referencia

La implementacion futura debe separar identidad interna de presentacion. El patron conceptual es:

```text
document = respuesta_api.documents[i]
row.dataset.documentId = document.id       # identidad interna no visible
name.textContent = document.filename       # dato mostrado como texto
status.textContent = humanStatus(document) # copy orientado al cliente
```

El identificador completo puede permanecer en un estado privado necesario para la accion. Nunca
se debe derivar un texto visible desde `document.id`, `document.sha256` o su prefijo.

## Estrategia de pruebas

### Unitarias y de contrato

- verificar que el listado conserva los campos internos necesarios sin exponerlos en el DOM;
- probar duplicados por SHA sin mostrar la identidad tecnica;
- conservar pruebas de toggle, preview, delete, estados `needs_ocr` y `error`;
- comprobar que el HTML/Markdown se mantiene literal y no ejecutable;
- comprobar que una mutacion usa el hash completo aunque no sea visible;
- verificar que un segundo delete devuelve `404` y que la fuente no vuelve al RAG.

### Smoke de navegador

No existe aun un runner browser en el checkout. Antes de declarar este fix implementado, realizar
el siguiente recorrido manual en Chrome y Edge:

1. abrir `/admin` a 1280 px con preview cerrado y confirmar ancho completo;
2. abrir preview y confirmar dos columnas sin una tercera zona vacia;
3. cerrar preview y confirmar que el inventario vuelve a ocupar todo el ancho;
4. repetir en 320, 375, 540, 768 y 1024 px;
5. verificar que no existe scroll horizontal de pagina ni del inventario;
6. subir PDF, TXT y MD, y revisar todos los estados;
7. confirmar que no aparece `SHA`, `sha256`, `document_id` ni un prefijo hexadecimal;
8. habilitar, deshabilitar y eliminar una fuente usando solo botones contextuales;
9. navegar por teclado y comprobar foco, lector de pantalla y confirmacion;
10. insertar un nombre con HTML y confirmar que se muestra como texto literal.

### Comandos de verificacion propuestos

```text
python -m pytest tests/test_admin_lifecycle.py tests/test_api.py tests/test_live_knowledge.py tests/test_http_contracts.py -q --basetemp <temp>/admin-ux
ruff check .
node --check app/web/app.js
git diff --check
```

`node --check` solo valida JavaScript. No sustituye el smoke visual ni prueba ausencia de scroll.

## Criterios de aceptacion

- **ADMIN-UX-AC-01:** con preview cerrado, el inventario usa toda la zona horizontal util y no
  existe una columna vacia reservada.
- **ADMIN-UX-AC-02:** con preview abierto en escritorio, inventario y preview se distribuyen en
  dos zonas legibles; al cerrar, la segunda zona desaparece del layout.
- **ADMIN-UX-AC-03:** a 320, 375, 540, 768, 1024 y 1280 px no se requiere scroll horizontal para
  leer una fuente, sus estados y sus acciones.
- **ADMIN-UX-AC-04:** ninguna informacion funcional desaparece en movil; se reorganiza en una ficha
  o equivalente accesible.
- **ADMIN-UX-AC-05:** no aparece el SHA completo, abreviado, `id`, `document_id` ni una accion de
  copiar identidad en la UI visible o accesible.
- **ADMIN-UX-AC-06:** las acciones siguen usando el identificador completo interno y conservan los
  contratos HTTP existentes.
- **ADMIN-UX-AC-07:** procesamiento y publicacion se muestran como estados separados, con texto
  humano y sin depender del color.
- **ADMIN-UX-AC-08:** deshabilitar no borra ni oculta la ficha; eliminar sigue siendo explicito,
  irreversible y auditable.
- **ADMIN-UX-AC-09:** HTML, Markdown y prompt injection se renderizan como texto literal.
- **ADMIN-UX-AC-10:** carga, vacio, error, OCR y mutacion tienen mensajes orientados al cliente y
  no filtran excepciones o rutas.
- **ADMIN-UX-AC-11:** foco, teclado, zoom, lector de pantalla y objetivos tactiles funcionan en
  la vista cerrada y abierta.
- **ADMIN-UX-AC-12:** la correccion no cambia elegibilidad RAG, corpus revision, snapshots ni
  comportamiento de upload/delete.

## Trazabilidad y sincronizacion obligatoria

| Requisito | Fuente | Verificacion futura |
|---|---|---|
| Inventario full-width | encargo Spec 1, `app/web/styles.css` | smoke de viewports |
| Sin SHA visible | encargo Spec 1, `app/web/app.js` | inspeccion DOM y smoke |
| Identidad interna estable | Spec 04, `app/main.py`, `documents.py` | pruebas API de acciones |
| Preview seguro | Spec 04 | `tests/test_admin_lifecycle.py` |
| Estado RAG | Spec 04, Spec 06 | tests de toggle/live knowledge |
| Evidencia honesta | Spec 07 | registro de comando y recorrido |

Antes de implementar:

1. actualizar la seccion UI de Spec 04;
2. actualizar D1/D3 y las filas `TRZ-ADMIN-*` de Spec 06;
3. agregar pruebas de DOM/layout o un smoke manual fechado en Spec 07;
4. reflejar el cambio en `README.md`, `docs/arquitectura.md` y el indice documental;
5. solo despues modificar `app/web/`.

## Limites

- **Siempre:** separar identidad interna de copy visible, resolver el layout por estado del
  preview, mantener datos funcionales, validar contenido no confiable y documentar viewports.
- **Preguntar antes:** cambiar endpoints, quitar campos internos de API, introducir un framework
  visual, exponer `/admin` fuera de localhost o convertir el inventario en una pagina publica.
- **Nunca:** mostrar SHA por comodidad de depuracion, usar un prefijo como identidad, esconder el
  overflow con CSS global, eliminar datos funcionales para que quepan o declarar un smoke manual
  como prueba automatizada.

## Preguntas abiertas

1. Confirmar si el preview de la Spec 09 sera un `dialog` nativo o un panel modal propio; esta spec
   solo exige que su estado no reserve espacio cuando esta cerrado.
2. Confirmar si la revision del corpus se necesita para diagnostico de administrador; la propuesta
   la retira de la vista principal por ser un dato interno.
3. Confirmar si el smoke browser se incorporara a una herramienta aprobada o continuara manual,
   sin romper el setup de 15 minutos.
