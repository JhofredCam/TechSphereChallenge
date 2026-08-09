# Spec: Explorador HTML de arquitectura y flujo del sistema

**ID:** `ARCH-EXPLORER-001`
**Estado:** `PROPOSED`; el HTML, CSS y JavaScript aun no se generan
**Version:** 0.1.0
**Fecha:** 2026-08-08
**Fuente normativa:** [`06_system_flow_diagram_specification.md`](06_system_flow_diagram_specification.md)
**Vista publicada:** [`docs/arquitectura.md`](../docs/arquitectura.md)

## Objetivo

Definir un artefacto documental independiente que permita a una persona buscar, filtrar y
entender como funciona cada parte del MVP con mas profundidad que un diagrama estatico. El
artefacto futuro sera un HTML con CSS y JavaScript locales, ejecutable sin servidor y sin acceso a
datos del runtime.

El explorador debe convertir la trazabilidad existente en una experiencia de consulta:

- mapa de extremo a extremo;
- vistas D1 a D6 de la Spec 06;
- catalogo de actores, superficies, APIs, etapas, modulos, estados, reglas, metricas, pruebas,
  gates y requisitos trazables;
- buscador por lenguaje de arquitectura y por identificador;
- panel de detalle con responsabilidad, entradas, salidas, codigo, pruebas, evidencia y limites;
- explicacion honesta de `IMPLEMENTED`, `TESTED`, `MANUAL_PENDING`, `PROPOSED` y `OUT_OF_SCOPE`.

No es una herramienta clinica, no es una consola de administracion y no ejecuta una llamada.

## Resultado esperado

Una persona que no conoce el repositorio debe poder responder desde el HTML:

1. quien inicia cada flujo;
2. que componente recibe la solicitud;
3. donde se decide el triaje;
4. como se recupera y cita el conocimiento;
5. que ocurre cuando no hay evidencia;
6. como se aprende, deshabilita y olvida una fuente;
7. que datos persisten y que metricas se miden;
8. que esta probado y que sigue pendiente de navegador, proveedor o evidencia externa.

## Supuestos explicitos

1. La Spec 06 continua siendo la unica autoridad normativa del flujo y de los IDs.
2. El HTML es una vista derivada y no puede corregir silenciosamente una contradiccion en la
   spec, el codigo o la evidencia.
3. El catalogo se genera de forma estatica y se embebe en el artefacto para que `file://` funcione
   sin CORS, API ni `fetch`.
4. El documento no contiene pacientes, conversaciones reales, corpus completo, archivos subidos,
   SQLite, JSONL ni secretos.
5. Las rutas de codigo y pruebas son referencias documentales; el explorador no las ejecuta.
6. La version exacta de la Spec 06, la fecha y el commit del catalogo deben ser visibles.
7. `DIVERGENCE` es una anotacion de sincronizacion, no un estado de implementacion.

## Tech Stack y restricciones

- HTML semantico estatico.
- CSS local sin framework obligatorio.
- JavaScript local sin bundler obligatorio, sin eval y sin dependencias remotas.
- SVG local o estructura HTML accesible para diagramas derivados.
- No depender de Mermaid en tiempo de ejecucion, CDN, fuentes web, iconos externos o API.
- No pedir permiso de microfono, no abrir `/call` y no cargar `data/`.
- No incorporar una nueva dependencia al setup base hasta que se justifique su impacto en G2.

## Artefactos futuros

La implementacion posterior debe producir, fuera de `app/web/`:

```text
docs/architecture_explorer.html       -> shell, contenido y landmarks
docs/architecture_explorer.css        -> layout, colores, estados y responsive
docs/architecture_explorer.js         -> busqueda, filtros, fragmentos y paneles
docs/architecture_explorer.data.js   -> catalogo estatico generado y versionado
```

La ruta no debe confundirse con `/admin` ni `/call`. Si posteriormente se sirve desde FastAPI,
debe existir una ruta documental separada, por ejemplo `/architecture`, sin heredar el estado de
una llamada ni acceso a APIs de conocimiento.

## Procedencia y modelo de datos

### Precedencia

El catalogo debe respetar:

```text
fuentes canonicas
  -> specs 00/03/04/05/06/07
  -> vistas publicadas
  -> codigo y contratos
  -> pruebas y evidencia fechada
```

Cuando dos fuentes difieren, la ficha debe mostrar la divergencia y enlazar la fuente
responsable. No se debe elegir la version mas conveniente para que el mapa parezca completo.

### Fuentes permitidas

- `specs/00_mvp_specification.md` y specs derivadas.
- `specs/06_system_flow_diagram_specification.md` como autoridad principal.
- `docs/arquitectura.md` y `mvp/deliverables/02_architecture/architecture.md` como vistas.
- `app/main.py`, `app/config.py`, `app/database.py` y `app/services/` como referencias de runtime.
- `app/web/` solo para explicar superficies y contratos de navegador.
- `tests/`, `docs/informe-final.md` y `readme/04_metricas_y_evidencia.md` para evidencia.

### Entrada del catalogo

Cada entidad debe contener, como minimo:

| Campo | Requisito |
|---|---|
| `entity_id` | ID estable de Spec 06 |
| `kind` | actor, UI, API, etapa, modulo, externo, dato, estado, regla, metrica, trazabilidad, prueba o gate |
| `title` | nombre humano corto |
| `summary` | explicacion de una frase |
| `description` | detalle para el panel profundo |
| `status` | uno de los cinco estados normativos |
| `status_scope` | a que evidencia aplica el estado |
| `views` | D1 a D6 relacionadas |
| `stages` | etapas `STG-*` relacionadas |
| `inputs` | entradas esperadas, sin datos reales |
| `outputs` | salidas observables |
| `invariants` | reglas que no se pueden romper |
| `code_refs` | rutas y simbolos de codigo |
| `test_refs` | pruebas y comandos |
| `source_refs` | spec, documento y ancla |
| `related_ids` | origen, destinos y dependencias |
| `evidence` | comando/recorrido, fecha, entorno y resultado |
| `divergences` | limites o contradicciones conocidas |
| `tags` | busqueda por dominio y superficie |
| `generated_at` | fecha de generacion del catalogo |
| `source_spec_version` | version de Spec 06 |
| `commit` | commit o `working tree/no commit` |

No se permiten registros sin `source_refs`, `status` o `entity_id`.

### Cobertura del catalogo

El catalogo debe incluir todos los prefijos definidos por Spec 06:

`ACT`, `UI`, `API`, `STG`, `MOD`, `EXT`, `DATA`, `STATE`, `RULE`, `MET`, `TRZ`, `TEST` y `GATE`.

Como minimo debe localizarse:

- `ACT-PATIENT-001`, `ACT-ADMIN-001`, `ACT-BROWSER-001`;
- `UI-ADMIN-001`, `UI-CALL-001`, `UI-TEXT-FALLBACK-001`;
- `API-ADMIN-LIST-001`, `API-ADMIN-PREVIEW-001`, `API-ADMIN-SOURCE-001`,
  `API-ADMIN-TOGGLE-001`, `API-ADMIN-DELETE-001`, `API-CALL-TURN-001`;
- `STG-BOOT-001` a `STG-CLOSE-001`;
- `MOD-RAG-001`, `MOD-AGENT-001`, `MOD-TRIAGE-001`, `MOD-DOCUMENT-001`,
  `MOD-INGEST-001`, `MOD-CALL-001`, `MOD-METRICS-001`;
- todos los estados de documento y escucha;
- reglas rojas, amarillas, desconocidas, de seguridad y de elegibilidad RAG;
- metricas de voz, tokens, invocaciones, consultas, timeout y costo;
- `TRZ-*`, `TEST-*` y `GATE-G1-001` a `GATE-G5-001`.

Una capacidad `PROPOSED` puede aparecer en el catalogo, pero debe indicar claramente que no
existe en el runtime actual. Una capacidad `MANUAL_PENDING` puede tener codigo y pruebas locales,
pero la ficha debe mostrar que esas pruebas no aprueban por si solas el gate externo.

## Navegacion y arquitectura de la pagina

### Landmarks

El documento debe tener:

- `header` con titulo, version y advertencia de uso;
- `nav` con enlace de salto, vistas D1-D6 y secciones principales;
- `main` con resultados, diagramas y detalles;
- `aside` o dialog para detalle de entidad;
- `footer` con procedencia, fecha y estado de sincronizacion.

### Secciones

1. Inicio y advertencia.
2. Flujo completo de las etapas 0 a 9.
3. Vistas D1, D2, D3, D4, D5 y D6.
4. Catalogo de componentes.
5. Contratos HTTP y persistencia.
6. Estados de implementacion y evidencia.
7. Metricas y gates.
8. Divergencias y limites.
9. Glosario y fuentes.

### Flujo completo

La pagina debe mostrar en orden:

`STG-BOOT-001`, `STG-ADMIN-001`, `STG-CALL-001`, `STG-VOICE-001`, `STG-TRIAGE-001`,
`STG-RAG-001`, `STG-AGENT-001`, `STG-TTS-001`, `STG-OBS-001`, `STG-CLOSE-001`.

Cada etapa muestra resumen, entrada, salida y boton para abrir el detalle de sus entidades.
Seleccionar una etapa filtra visualmente el catalogo sin borrar la consulta textual.

### Vistas D1-D6

| Vista | Pregunta que responde |
|---|---|
| D1 | quien participa, que posee cada bloque y donde vive |
| D2 | como transcurre una llamada, escucha, timeout e idempotencia |
| D3 | como se sube, inspecciona, publica y elimina conocimiento |
| D4 | como se separan triaje, RAG, agente, citas y abstencion |
| D5 | que estados atraviesa la escucha y que significa un fallback |
| D6 | que se persiste, que se mide y que evidencia existe |

Cada vista debe tener:

- titulo con ID y pregunta de usuario;
- diagrama o mapa estructurado;
- equivalente textual en orden de lectura;
- leyenda de colores, formas, relaciones y estados;
- nodos seleccionables;
- enlaces a fichas relacionadas;
- referencia a la seccion de Spec 06 que la gobierna.

## Busqueda y filtros

### Busqueda global

La busqueda debe cubrir ID, titulo, alias, resumen, descripcion, rutas de codigo, rutas HTTP,
nombres de pruebas, comandos, estados, gates, vistas, etapas, tags y glosario.

Requisitos:

- insensible a mayusculas;
- tolerante a tildes y variaciones de guion/underscore;
- acepta frase exacta y varios terminos;
- prioriza coincidencia exacta de ID, luego titulo, ruta, estado y descripcion;
- resalta coincidencias de forma segura, sin insertar HTML desde la consulta;
- muestra numero de resultados y filtros activos;
- ofrece limpiar busqueda;
- conserva la consulta en el fragmento URL.

Consultas que deben funcionar:

`rag`, `available enabled`, `late_transcript`, `PATIENT_LISTEN_TIMEOUT_MS`, `delete`, `G5`,
`MANUAL_PENDING`, `prompt injection`, `app/services/agent.py`, `no_current_evidence`.

### Filtros combinables

- tipo de entidad;
- estado de evidencia;
- vista D1-D6;
- etapa STG;
- superficie: admin, call, API, voz, datos, CLI;
- ownership: usuario, admin, bot, RAG, datos, externo, seguridad, metricas;
- gate;
- fuente documental;
- tiene prueba automatizada;
- tiene evidencia manual pendiente;
- solo propuestas/fuera de alcance.

Cada filtro muestra su conteo y permite limpiar todos. Una combinacion vacia debe explicar que
debe cambiar el usuario, no mostrar una pagina en blanco sin contexto.

No debe existir un campo de busqueda de pacientes ni un texto que sugiera que la pagina ejecuta
consultas clinicas.

### Estado en el fragmento URL

La seleccion debe poder compartirse y sobrevivir a recarga mediante fragmentos locales, por
ejemplo:

```text
#q=timeout&status=MANUAL_PENDING&entity=STATE-VOICE-TIMEOUT-001&view=D5
```

Debe funcionar con `file://`, atras, adelante y enlaces internos. Valores desconocidos se ignoran
de forma segura sin ejecutar una URL arbitraria.

## Panel de detalle

Al seleccionar una entidad, se abre un panel lateral en escritorio y una vista completa o dialog
en movil. El panel muestra:

- ID, tipo, nombre y ownership;
- resumen y descripcion profunda;
- estado y alcance exacto de ese estado;
- entradas, salidas y limites;
- invariantes y reglas de seguridad;
- rutas de codigo y simbolos;
- contrato HTTP, si aplica;
- tablas o entidades persistidas relacionadas;
- pruebas, comandos y resultados;
- evidencia manual pendiente;
- vistas, etapas y entidades relacionadas;
- divergencias y fuente responsable;
- version, fecha y commit de la procedencia.

Para una API debe mostrar metodo, ruta, proposito, entradas, salidas y errores relevantes. Para
una metrica debe mostrar definicion, timestamps, fuente y si es real, estimada o pendiente. Para
un gate debe mostrar evidencia requerida y por que las pruebas locales no lo aprueban.

El panel no puede mostrar claves, tokens, `stored_path`, audio, pacientes, filas XLSX, texto
completo de documentos, `data/app.sqlite3` ni `data/events.jsonl`.

Interaccion requerida:

- abrir por teclado;
- cerrar con Escape y control visible;
- devolver foco al elemento que abrio el detalle;
- usar nombre accesible y `aria-expanded`/`aria-controls`;
- conservar entidad y filtros en fragmento;
- permitir navegar a entidades relacionadas sin perder la consulta.

## Convenciones visuales

El explorador debe heredar la paleta de la Spec 06:

| Ownership | Color | Forma o etiqueta adicional |
|---|---|---|
| Usuario | azul | actor y `[USUARIO]` |
| Admin | ambar | actor/admin y `[ADMIN]` |
| Bot | violeta | proceso y `[BOT]` |
| RAG | turquesa | proceso de recuperacion y `[RAG]` |
| Datos | gris | cilindro/almacen y `[DATOS]` |
| Externo | naranja | borde discontinuo y `[EXTERNO]` |
| Seguridad | rojo | decision/regla y `[SEGURIDAD]` |
| Metricas | verde | evidencia/medicion y `[METRICAS]` |

La forma expresa tipo de entidad; el color expresa ownership; el texto expresa estado. El
significado debe permanecer en escala de grises, alto contraste y lector de pantalla.

Relaciones que deben poder explicarse:

- `HTTP` entre browser y API;
- `DB` entre servicios y persistencia;
- `RAG` entre pregunta, recuperador y chunks;
- `STT` y `TTS` en voz;
- `T=` para limites temporales;
- dependencia opcional;
- evidencia de prueba;
- snapshot historico no reutilizable.

## Accesibilidad y responsive

- `lang="es"`, HTML semantico y jerarquia correcta de encabezados;
- enlace `Saltar al contenido`;
- navegacion por teclado completa y foco visible;
- objetivo tactil aproximado de 44 px;
- contraste WCAG AA;
- no depender del color, hover o tooltip para revelar un significado;
- reflow sin scroll horizontal a 320 px y zoom de 200 % y 400 %;
- navegacion lateral plegable en movil;
- detalle lateral convertido a dialog/seccion completa en movil;
- tablas convertibles a fichas sin perder columnas;
- `aria-live` para resultado de busqueda y filtros;
- `aria-current` para vista activa;
- `aria-expanded` para filtros y secciones plegables;
- `prefers-reduced-motion` y CSS de impresion;
- cada diagrama tiene titulo, descripcion y equivalente textual.

## Seguridad offline

El HTML debe abrir directamente como archivo local y mantenerse completamente aislado:

- cero `fetch`, WebSocket, API, analitica o solicitudes de red;
- cero CDN, fuentes externas, imagenes remotas o iconos descargados;
- cero permisos de microfono y cero llamadas a `/admin` o `/call`;
- no leer `data/`, `dataset/`, uploads ni variables de entorno;
- no usar `eval`, `Function`, handlers inline ni scripts dinamicos;
- no usar `innerHTML` con datos de busqueda, catalogo o nombres de archivos;
- crear contenido con nodos DOM y texto seguro;
- validar entidad, estado, vista y relaciones contra el catalogo;
- ignorar `javascript:` y URLs externas en enlaces derivados;
- mantener estado en memoria y fragmento, sin `localStorage` salvo aprobacion explicita;
- incluir advertencia de que es un documento y no una superficie clinica.

El catalogo debe estar embebido o cargarse desde un archivo JavaScript local incluido por referencia
relativa. No se debe depender de `fetch('catalog.json')`, porque puede fallar al abrir con
`file://`.

## Glosario minimo

El explorador debe explicar, con lenguaje no tecnico primero y detalle bajo demanda:

- `available`, `enabled`, `rag_eligible` y `needs_ocr`;
- FTS5, chunk, score BM25 y cita;
- `corpus_revision` y snapshot historico;
- `listen_id`, `client_turn_id` y `late_transcript`;
- grounding, abstencion, fallback y prompt injection;
- `IMPLEMENTED`, `TESTED`, `MANUAL_PENDING`, `PROPOSED`, `OUT_OF_SCOPE` y `DIVERGENCE`;
- gates G1 a G5 y metricas P50/P95, tokens, llamadas, consultas RAG y costo.

## Code Style futuro

Aunque esta entrega no implementa el artefacto, la futura implementacion debe cumplir:

- nombres de archivos y funciones en ingles descriptivo o el estilo que ya use el repositorio;
- IDs de entidades canonicos sin renombrar aliases de Mermaid;
- funciones pequenas para indexar, filtrar, renderizar y actualizar URL;
- `textContent`/nodos DOM para datos, no concatenacion HTML;
- CSS por capas: layout, componentes, estados, responsive e impresion;
- copy en espanol claro, sin exponer nombres internos como unica explicacion;
- comentarios solo para decisiones no obvias de seguridad/procedencia;
- no duplicar la autoridad de Spec 06 dentro del HTML.

## Comandos de verificacion

Los comandos definitivos deben reflejar los archivos realmente generados. El contrato minimo
propuesto es:

```text
node --check docs/architecture_explorer.js
python -m pytest tests/test_architecture_explorer.py -q --basetemp <temp>/architecture-explorer
python -c "from pathlib import Path; required = ['docs/architecture_explorer.html', 'docs/architecture_explorer.css', 'docs/architecture_explorer.js', 'docs/architecture_explorer.data.js']; missing = [p for p in required if not Path(p).is_file()]; assert not missing, missing"
git diff --check
```

El HTML debe probarse adicionalmente abriendo `file://` en Chrome y Edge. La comprobacion de
sintaxis JavaScript no demuestra busqueda, accesibilidad, ausencia de red o comportamiento
responsive.

## Estrategia de pruebas

### Pruebas estaticas

- HTML valido y referencias relativas existentes;
- JavaScript sintacticamente valido;
- IDs unicos, prefijos permitidos y estados normativos;
- todas las relaciones apuntan a entidades existentes;
- cada entidad tiene procedencia y estado;
- existen D1-D6, STG-BOOT a STG-CLOSE y gates G1-G5;
- no aparecen `fetch`, WebSocket, `eval`, `innerHTML`, URLs externas, secretos, `stored_path`,
  `data/`, pacientes o corpus completo;
- el catalogo declara version, fecha y commit;
- la paleta y las etiquetas obligatorias se aplican a cada tipo.

### Smoke offline

1. abrir el HTML con `file://` sin Uvicorn;
2. observar consola y Network, sin errores ni solicitudes;
3. buscar `late_transcript`, `G5`, `MANUAL_PENDING` y `app/services/agent.py`;
4. combinar filtros de estado, vista, etapa y ownership;
5. abrir `MOD-RAG-001`, `API-CALL-TURN-001` y `STATE-VOICE-TIMEOUT-001`;
6. navegar D1 a D6 y volver con atras/adelante;
7. usar teclado, lector de pantalla, zoom, movil y reduccion de movimiento;
8. imprimir y comprobar que la procedencia y el equivalente textual permanecen;
9. confirmar que no se pide microfono ni se muta el runtime.

### Frontera de evidencia

El explorador puede documentar `TESTED`, pero no convierte su presencia en aprobacion de G2, G3,
G4 o G5. La evidencia de navegador, proveedor real, cronometraje y documento externo sigue en
`MANUAL_PENDING` hasta su recorrido propio.

## Criterios de aceptacion

- **ARCH-EXPLORER-AC-01:** el HTML abre desde `file://` sin servidor, dependencias externas ni
  solicitudes de red.
- **ARCH-EXPLORER-AC-02:** cubre D1-D6, las diez etapas STG y los prefijos de entidades de Spec 06.
- **ARCH-EXPLORER-AC-03:** busca por ID, ruta, estado, gate, vista, etapa y texto descriptivo,
  tolerando tildes y mayusculas.
- **ARCH-EXPLORER-AC-04:** combina filtros, muestra conteos y conserva busqueda/filtros en URL
  local sin ejecutar valores arbitrarios.
- **ARCH-EXPLORER-AC-05:** cada entidad abre detalle con procedencia, entradas, salidas, codigo,
  pruebas, evidencia, dependencias, invariantes y limites.
- **ARCH-EXPLORER-AC-06:** diferencia capacidad existente, prueba automatizada, evidencia manual,
  propuesta, fuera de alcance y divergencia.
- **ARCH-EXPLORER-AC-07:** diagramas, formas, colores, leyenda y equivalente textual explican
  ownership sin depender solo del color.
- **ARCH-EXPLORER-AC-08:** el panel de detalle es usable con teclado, lector de pantalla, zoom,
  movil, impresion y `prefers-reduced-motion`.
- **ARCH-EXPLORER-AC-09:** no contiene pacientes, secretos, rutas de uploads, base local, eventos,
  corpus completo ni APIs ejecutables.
- **ARCH-EXPLORER-AC-10:** no se mezcla con `/admin` o `/call`, no solicita microfono y no cambia
  ningun gate o estado del runtime.
- **ARCH-EXPLORER-AC-11:** la pagina muestra version de Spec 06, fecha, commit y precedencia de
  fuentes.
- **ARCH-EXPLORER-AC-12:** una entidad pendiente conserva la palabra `MANUAL_PENDING` o
  `PROPOSED` y explica la evidencia que falta.
- **ARCH-EXPLORER-AC-13:** las propuestas de Spec 08 y Spec 09 aparecen como futuras, no como
  funciones implementadas.

## Trazabilidad y sincronizacion

Antes de implementar el HTML:

1. mantener Spec 06 como fuente normativa y actualizarla primero ante un cambio de flujo;
2. registrar en el catalogo la version de Spec 06 y el commit de generacion;
3. enlazar desde `README.md`, `readme/00_indice_de_documentacion.md`, `docs/arquitectura.md` y
   `mvp/deliverables/02_architecture/architecture.md`;
4. extender Spec 07 con pruebas estaticas y smoke offline, sin convertirlos en G4/G5;
5. registrar la existencia, comandos y resultado en `readme/04_metricas_y_evidencia.md`;
6. regenerar el catalogo cuando cambien IDs, estados, contratos o diagramas;
7. no editar manualmente el HTML para ocultar una divergencia del runtime.

## Limites

- **Siempre:** mantener procedencia, estado honesto, navegacion offline, texto accesible, no
  exponer datos del runtime y sincronizar con Spec 06.
- **Preguntar antes:** servir el HTML desde FastAPI, agregar CDN, instalar Playwright, usar una
  base de datos documental, incluir Mermaid en runtime o mostrar ejemplos con datos de pacientes.
- **Nunca:** convertir el explorador en UI clinica, ejecutar endpoints, leer SQLite, afirmar un
  gate aprobado por el catalogo o crear una segunda autoridad de arquitectura.

## Preguntas abiertas

1. Confirmar si el artefacto debe permanecer solo como archivo local o tambien publicarse en una
   ruta documental de FastAPI.
2. Confirmar si los diagramas se generaran como SVG local o como HTML estructurado sin SVG.
3. Confirmar si se acepta una dependencia de generacion temporal, siempre que no entre al setup
   base ni se use en tiempo de ejecucion.
4. Confirmar si el catalogo generado se versiona completo o se reconstruye en cada entrega con
   evidencia de su commit de origen.
