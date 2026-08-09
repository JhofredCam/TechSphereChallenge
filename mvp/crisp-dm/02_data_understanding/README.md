# 02 - Data Understanding

## Objetivo

Conocer la forma, cobertura y riesgos de los insumos locales antes de implementar ingestion
o triaje. El resultado debe permitir validar los XLSX y recorrer el corpus PDF sin asumir que
una fila es una llamada ni que todo PDF tiene capa de texto.

## Entradas

- [`dataset/`](../../../dataset/), que es la copia canonica y no debe moverse.
- [Descripcion de los datos y bootstrap](../../../README.md#datos-y-bootstrap).
- [Trampas de datos del repositorio](../../../AGENTS.md#dataset-traps).
- [Tareas de validacion del dataset](../../../specs/02_implementation_tasks.md).

## Salidas

- Inventario reproducible de los cuatro XLSX y sus hojas `result`.
- Validacion de encabezados, filas esperadas, JSON embebido y joins por `paciente_id` y
  `caso_id = "caso_" + trayectoria_id`.
- Registro de que `dataset_final.xlsx` es turn-level y debe filtrarse por `capa` antes de
  reconstruir conversaciones.
- Inventario recursivo de `dataset/textos/`, incluyendo espacios, duplicados y el PDF
  escaneado que debe quedar como `needs_ocr`.
- Riesgos de calidad y limites de uso: datos sinteticos, desbalance y material clinico no
  necesariamente presente en evaluacion.

## Tareas concretas

1. Enumerar los cuatro XLSX y confirmar que cada uno tiene una sola hoja llamada `result`.
2. Revisar encabezados, dimensiones y tipos sin cargar `label_ground_truth` como contexto del
   paciente.
3. Parsear `comorbilidades` y `adaptation_fields` como listas JSON dentro de una celda.
4. Filtrar `capa1_limpia` y `capa2_ruidosa`; reconocer sufijos `_c2` y `_c2_tercero`.
5. Validar el join entre perfiles, conversaciones y trayectorias sin convertir turnos en
   llamadas por posicion.
6. Recorrer `dataset/textos/` de forma recursiva, preservando rutas con espacios y nombres
   repetidos.
7. Detectar paginas sin texto y documentar el estado `needs_ocr`; nunca presentarlo como
   conocimiento disponible.

## Criterios de aceptacion

- [x] El validador confirma hojas, encabezados, filas, JSON y joins sin mezclar capas.
- [x] El inventario identifica todas las rutas de origen y conserva entradas duplicadas como
  reportes distinguibles, aunque el almacenamiento deduplica por hash.
- [x] El PDF escaneado queda identificado como `needs_ocr` y no genera citas falsas.
- [x] Existe un registro de conteos y salida fechado que puede repetirse sin descargar datos.
- [x] Ningun campo de referencia de criticidad se usa como contexto de la conversacion.

## Verificacion y evidencia

Comando ejecutado desde la raiz:

```text
python -m scripts.validate_dataset
```

Evidencia obtenida el 2026-08-08:

```text
python -m scripts.validate_dataset
```

El comando confirmo `dataset validation: valid` y las filas `3991`, `40`, `40` y `160`
para los cuatro XLSX. La validacion es de solo lectura. El bootstrap recorrio el corpus de
forma recursiva y dejo 1 documento en `needs_ocr`; sus rutas, espacios y hashes se mantienen
en el reporte sin copiar el dataset.

## Dependencias

- Depende de la estructura canonica de `dataset/` y de los contratos descritos en el README.
- La fase 03 necesita sus reglas de filtros, joins y estados de extraction.
- La fase 05 necesita un baseline de datos para distinguir fallas de ingestion de fallas del
  agente.

## Estado

**Validada - XLSX y corpus local verificados (2026-08-08).**
