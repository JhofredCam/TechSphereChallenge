# 2026-08-09 | Correcciones de preview PDF y UX conversacional

## Alcance

Se revisó lo conversado sobre las Specs 09 y 11 y se actualizaron sus contratos documentales.
También quedó registrada la implementación previa de las Specs 09, 10 y 11 en ramas separadas,
conforme a la política de ramas del repositorio.

## Decisiones y archivos

- `specs/09_admin_source_preview_specification.md`: el PDF debe abrirse directamente dentro de
  un modal accesible mediante un visor embebido (`iframe` u `object`) con MIME
  `application/pdf`. Abrir una pestaña nueva, descargarlo o mostrar solo texto extraído no
  cumple el requisito.
- `specs/11_conversational_ux_writing_specification.md`: se eliminó del contrato la presión
  temporal; la escucha queda abierta hasta la finalización explícita del paciente, cierre de
  llamada o fallo técnico real.
- La spec 11 define `patient_text` como fuente canónica. `voice_text`, `display_text`, la
  burbuja visible y `SpeechSynthesisUtterance.text` deben ser idénticos; la trazabilidad queda en
  `source_display` y no se pronuncia.
- La spec 11 quedó marcada `SPEC_UPDATED`, porque el runtime todavía requiere migración para
  retirar `PATIENT_LISTEN_TIMEOUT_MS`, la cuenta regresiva y la divergencia entre audio y UI.

## Ramas y commits publicados

- `spec/09-admin-source-preview` — `9f171d8`, implementación del preview original.
- `spec/10-architecture-explorer` — `8c2a91f`, explorador de arquitectura offline.
- `spec/11-conversational-ux` — `ab8eb26`, catálogo y UX conversacional inicial.
- `spec/09-pdf-modal-requirement` — `e48a99f`, requisito de PDF directo dentro del modal.
- `spec/11-open-listening-audio-parity` — `18f6aaa`, escucha abierta y paridad audio-texto.

## Verificación

- Suite completa previa: `106 passed`.
- Ruff, `node --check` y `git diff --check`: aprobados en la implementación previa y en las
  correcciones documentales.
- Validación del dataset: `Dataset validation: valid`.

## Pendientes y riesgos

- La migración de runtime de la Spec 11 y el smoke real en Chrome/Edge siguen pendientes.
- La visualización PDF depende del visor del navegador; puede permitir guardar o copiar el
  archivo, limitación documentada honestamente.
- El cambio preexistente de `AGENTS.md` se conservó fuera de los commits de esta sesión.

## Siguiente acción verificable

Implementar la escucha abierta y el canal canónico `patient_text` en el runtime, añadir la prueba
de igualdad exacta entre la burbuja y TTS, y ejecutar el smoke manual de voz y del modal PDF.
