# 2026-08-09 | Corrección del modal PDF en `/admin`

## Alcance

Se corrigió el comportamiento por el que la previsualización aparecía como una columna lateral
sticky en lugar de una ventana emergente superpuesta con el PDF.

## Cambios

- se eliminó la expansión de columnas `admin-workspace.preview-open`;
- el preview usa posición fija, ancho limitado, scroll interno y backdrop;
- el PDF continúa cargándose dentro del `iframe` del `dialog` con sus bytes originales;
- se agregó un fallback modal para navegadores sin `dialog.showModal()`;
- el cierre limpia el fallback, el backdrop, la URL temporal y devuelve el foco al botón invocador;
- se actualizó `tests/test_admin_ui_contracts.py` para impedir el regreso del panel lateral.

## Verificación

- `26 passed` en las pruebas enfocadas de administración, API y preview;
- Ruff, `node --check app/web/app.js` y `git diff --check` aprobados;
- el navegador in-app no estuvo disponible, por lo que el smoke visual queda
  `MANUAL_PENDING`.

## Pendiente

Confirmar en Chrome o Edge que el modal se superpone al inventario, que el PDF se muestra dentro
del visor y que Escape/cierre restauran el foco correctamente.
