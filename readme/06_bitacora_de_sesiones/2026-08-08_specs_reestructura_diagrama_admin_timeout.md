# Sesion de especificaciones - 2026-08-08

## Alcance

Crear cuatro specs y propagar el cambio en documentos, sin ejecutar specs, pruebas ni codigo:

1. Reestructurar entregables bajo `mvp/` y fases bajo `mvp/crisp-dm/`.
2. Definir el diagrama ASCII y Mermaid como fuente normativa del flujo completo.
3. Especificar preview, habilitar/deshabilitar y delete para `/admin`.
4. Especificar un timeout configurable de escucha y publicarlo en `.env.example`.

## Archivos normativos creados

- `specs/03_mvp_structure_specification.md`
- `specs/04_admin_document_lifecycle_specification.md`
- `specs/05_patient_listening_timeout_specification.md`
- `specs/06_system_flow_diagram_specification.md`

La dependencia se fijo en ese orden: estructura, admin, timeout y diagrama. El diagrama incluye
ASCII, contexto, llamada, ciclo documental, triaje/RAG, voz/timeout, metricas y matriz `TRZ-*`.

## Decisiones y supuestos

- `dataset/` y `docs/` siguen siendo canonicos y no se mueven ni se copian.
- `app/`, `scripts/`, `tests/`, `specs/`, `readme/` y `data/` no se duplican dentro de `mvp/`.
- La estructura objetivo usa `mvp/crisp-dm/` y `mvp/deliverables/`, pero la migracion fisica no
  se aplico.
- `/admin` separa estado tecnico (`available`, `needs_ocr`, etc.) de publicacion (`enabled`).
- La carga nueva se propone habilitada por compatibilidad con G5; requiere confirmacion humana.
- `.env.example` agrega `PATIENT_LISTEN_TIMEOUT_MS=30000` como valor provisional. La variable no
  tiene efecto en el runtime actual.
- La semantica elegida provisionalmente es limite total por turno, no timeout de silencio.
  Esta decision requiere confirmacion antes de implementar.
- El diagrama marca capacidades nuevas como `PROPOSED` y conserva la diferencia entre tests
  locales y evidencia manual G4/G5.

## Documentos propagados

- `README.md`
- `specs/00_mvp_specification.md`
- `specs/01_implementation_plan.md`
- `specs/02_implementation_tasks.md`
- `mvp/README.md`
- `mvp/01_business_understanding/README.md`
- `mvp/03_data_preparation/README.md`
- `mvp/04_modeling/README.md`
- `mvp/05_evaluation/README.md`
- `mvp/06_deployment/README.md`
- `docs/arquitectura.md`
- `docs/informe-final.md`
- `readme/00_indice_de_documentacion.md`
- `readme/02_setup_local.md`
- `readme/03_demo_funcional.md`
- `readme/04_metricas_y_evidencia.md`
- `readme/06_bitacora_de_sesiones/README.md`
- `.env.example`

## Verificacion de la sesion

Comando ejecutado:

```text
git status --short --branch
git diff --check
```

No se ejecutaron `pytest`, Ruff, bootstrap, servidor, smoke browser ni ninguna spec. `git diff
--check` solo reviso espacios del diff y no ejecuto el runtime. Los cambios
no relacionados que ya estaban sin seguimiento (`AGENTS.md` y `skills-lock.json`) se conservaron.

## Pendientes

- Confirmar si el timeout requerido es total, de silencio o ambos.
- Confirmar si la carga nueva debe entrar en cuarentena o quedar habilitada.
- Confirmar ownership final de `docs/arquitectura.md`, `docs/informe-final.md` y las vistas bajo
  `mvp/deliverables/`.
- Revisar y aprobar las cuatro specs antes de pasar a plan de implementacion.
