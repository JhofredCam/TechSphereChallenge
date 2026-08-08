# Sesion de especificacion de pruebas - 2026-08-08

## Alcance

Definir pruebas unitarias y de integracion para el MVP, sin ejecutar pruebas, servidor ni codigo.
La spec distingue el baseline actual de las extensiones propuestas en admin, timeout y diagrama.

## Documento creado

- `specs/07_testing_unit_integration_specification.md`

La spec cubre suite existente, contratos HTTP, fixtures, aislamiento, catalogos `UT-*` e `IT-*`,
cobertura pytest-cov, seguridad, comandos, compuertas G1-G5 y evidencia manual.

## Decisiones

- Las pruebas unitarias no requieren red, credenciales ni proveedores reales.
- Las pruebas de integracion usan SQLite/FTS5 real, servicios reales y `TestClient`, con Groq y
  Whisper sustituidos por adaptadores falsos.
- G4 requiere navegador, microfono y audio reales; G5 requiere documento externo al corpus.
- `preview`, `enabled`, timeout e idempotencia de `client_turn_id` permanecen como pruebas
  futuras mientras sus specs 04 y 05 no esten implementadas.
- La cobertura objetivo propuesta es 80 % del codigo propio, con prioridad en ramas P0.
- Cada resultado futuro debe conservar fecha, commit, entorno, comando o URL y artefacto.

## Documentos propagados

- `README.md`
- `docs/informe-final.md`
- `specs/00_mvp_specification.md`
- `specs/01_implementation_plan.md`
- `specs/02_implementation_tasks.md`
- `mvp/README.md`
- `mvp/crisp-dm/05_evaluation/README.md`
- `readme/00_indice_de_documentacion.md`
- `readme/04_metricas_y_evidencia.md`
- `readme/06_bitacora_de_sesiones/README.md`

## Verificacion de la sesion

No se ejecutaron pytest, pytest-cov, Ruff, bootstrap, servidor, smoke browser ni codigo. La
revision se realizo por lectura estatica y los comandos de prueba quedan como comandos previstos
dentro de la spec.

Los archivos sin seguimiento preexistentes `AGENTS.md` y `skills-lock.json` no se modificaron.

## Pendientes

- Confirmar el alcance formal del umbral de cobertura y de cobertura de ramas.
- Decidir si se incorpora automatizacion browser sin afectar el setup de 15 minutos.
- Resolver las decisiones abiertas de admin, timeout, aislamiento de `app.main` y matriz `TRZ-*`.
