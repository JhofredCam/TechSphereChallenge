# 2026-08-09 | Ajuste de headers y Blob URL para PDF en Chrome

## Alcance

Se atendió el bloqueo de Chrome al incrustar el PDF del preview administrativo.

## Cambios

- el endpoint entrega `Content-Type: application/pdf` y `Content-Disposition` con `inline`,
  `filename` y `filename*`;
- se conserva `X-Frame-Options: SAMEORIGIN` y no se entrega `DENY`;
- el iframe usa `fetch`, `response.blob()` y `URL.createObjectURL(blob)`;
- se retiró el `sandbox` del iframe PDF porque podía impedir la carga del visor nativo de Chrome;
- la spec 09 documenta la ausencia de CSP bloqueante y la revocación de Blob URLs;
- se añadieron regresiones HTTP y frontend para headers y Blob URL.

## Verificación

- pruebas enfocadas: `9 passed`;
- suite completa: `105 passed`;
- Ruff, `node --check app/web/app.js` y `git diff --check`: aprobados;
- smoke visual Chrome/Edge: `MANUAL_PENDING`, porque el navegador local no estuvo disponible.
