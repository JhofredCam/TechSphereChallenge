# Bitacora de sesiones

Esta carpeta conserva una entrada por sesión de trabajo. Cada entrada debe registrar:

- alcance y archivos tocados;
- decisiones tomadas y supuestos que requieren criterio;
- comandos ejecutados y resultados observables;
- riesgos, pendientes y la siguiente acción verificable.

## Entradas

- [2026-08-08 | Refactor y MVP CRISP-DM](2026-08-08_refactor_mvp.md)
- [2026-08-08 | Specs de estructura, diagrama, admin y timeout](2026-08-08_specs_reestructura_diagrama_admin_timeout.md)
- [2026-08-08 | Spec de pruebas unitarias e integracion](2026-08-08_specs_testing_unit_integration.md)
- [2026-08-08 | Specs de migracion RAG de produccion](2026-08-08_rag_production_migration_specs.md)
- [2026-08-09 | Correcciones de preview PDF y UX conversacional](2026-08-09_correcciones_specs_09_11.md)
- [2026-08-09 | Ajuste de headers y Blob URL para PDF en Chrome](2026-08-09_admin_pdf_chrome_headers.md)
- [2026-08-09 | Merge de sesiones ejecutor y planificador a `main`](2026-08-09_merge_sesiones_main.md)
- [2026-08-09 | Corrección del modal PDF en `/admin`](2026-08-09_admin_pdf_modal_runtime_fix.md)

## Entrada reciente

- [2026-08-09 | Verificacion end-to-end local](2026-08-09_verificacion_e2e.md)
- [2026-08-09 | Integracion del contexto oficial y guias de agente](2026-08-09_integracion_contexto_reto_guias_agente.md)
- [2026-08-09 | Specs de portal demo, UX de llamada y VAD](2026-08-09_specs_portal_demo_call_vad.md)
- [2026-08-09 | Orquestacion paralela de specs y cierre integrador](2026-08-09_orquestacion_specs_paralelo.md)

## Regla de integracion

Toda sesion de ejecutor o planificador que produzca cambios debe cerrar su rama dedicada
con commit, merge explicito a `main` y push de `main`. Una sesion no se considera integrada
hasta que sus cambios aparezcan en `main` y su resultado quede registrado en esta bitacora.

Usa nombres `YYYY-MM-DD_nombre_auto_explicativo.md` y no registres secretos, tokens ni datos
locales generados bajo `data/`.
