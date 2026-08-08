# 03 - Data Preparation

## Objetivo

Preparar los datos y el conocimiento para que el MVP pueda recuperarlos con trazabilidad,
sin alterar las fuentes canonicas. La preparacion cubre ingestion documental, SQLite/FTS5,
estado de disponibilidad y contratos de casos; no entrena un modelo clinico.

## Entradas

- Resultados de [Data Understanding](../02_data_understanding/README.md).
- Corpus canonico [`dataset/textos/`](../../dataset/textos/).
- XLSX canonicos bajo [`dataset/`](../../dataset/).
- [Arquitectura publicada del MVP](../../docs/arquitectura.md).
- Restriccion de [no mover `dataset/` ni `docs/`](../../specs/00_mvp_specification.md#supuestos-explicitos).
- [Ciclo documental de `/admin`](../../specs/04_admin_document_lifecycle_specification.md),
  que separa disponibilidad tecnica de publicacion activa.

## Salidas

- Base local en `data/` con esquema documental, chunks, fuentes y revision de corpus.
- Documentos en estados `available`, `needs_ocr` o `error`.
- Chunks por pagina con documento, pagina, chunk, cita y puntuacion recuperable.
- Indices SQLite FTS5 para consultas lexicales y borrado atomico.
- Contratos de casos preparados sin mezclar `capa1_limpia` con `capa2_ruidosa`.
- Registro de rutas, duplicados y fallas de extraction para auditoria.

## Tareas concretas

1. Crear configuracion de rutas con `pathlib` y mantener el estado generado fuera de las
   fuentes canonicas.
2. Recorrer PDFs, TXT y MD recursivamente, incluyendo rutas con espacios.
3. Extraer texto por pagina con PyMuPDF y clasificar el PDF escaneado como `needs_ocr`.
4. Normalizar texto, generar chunks acotados y conservar metadatos de documento, pagina,
   revision y ruta.
5. Insertar chunks y registros de documentos en SQLite con FTS5 y consultas parametrizadas.
6. Implementar upload, procesamiento, listado y delete como una transaccion que invalida
   resultados futuros sin reiniciar el servidor.
7. Validar los cuatro XLSX y dejar disponible la relacion de casos para pruebas, sin usar
   `label_ground_truth` como contexto del paciente.

## Criterios de aceptacion

- [x] `python -m app.bootstrap` crea base y directorios sin descargar modelos ni datos.
- [x] PDFs, TXT y MD procesables quedan en `available`; el escaneado queda en `needs_ocr`.
- [x] Cada resultado de recuperacion conserva documento, pagina, chunk y revision.
- [x] Una frase exclusiva de un documento subido se recupera antes de borrarlo y deja de
  aparecer despues del delete sin reiniciar.
- [x] Las rutas con espacios, duplicados y capas de conversaciones pasan la validacion.
- [x] Las consultas son parametrizadas y el estado parcial no se presenta como disponible.
- [ ] La futura bandera `enabled` conserva chunks y excluye documentos deshabilitados del RAG;
  esta ampliacion esta especificada pero no implementada en este corte.

## Verificacion y evidencia

Comandos ejecutados desde la raiz:

```text
python -m app.bootstrap --data-dir <temp>
python -m pytest -q --basetemp <temp>
```

Resultado del 2026-08-08: el bootstrap proceso 104 documentos, con 103 `available` y 1
`needs_ocr`. La suite de 38 tests paso e incluyo ingestion, API, RAG local, upload/delete,
trazabilidad y la prueba de idempotencia del bootstrap. La prueba de conocimiento vivo
confirmo recuperacion antes del borrado y ausencia posterior sin reiniciar el proceso.
Esto es evidencia local automatizada; la demostracion G5 con documento externo sigue
pendiente en [metricas y evidencia](../../readme/04_metricas_y_evidencia.md).

## Dependencias

- Depende de la fase 02 para conocer formatos y casos problematicos.
- Provee la base para RAG, triaje informado por contexto, upload/delete y metricas.
- Requiere PyMuPDF, openpyxl y SQLite FTS5 segun la especificacion del MVP.

## Estado

**Implementada - ingestion, bootstrap y conocimiento vivo local verificados (2026-08-08).**
