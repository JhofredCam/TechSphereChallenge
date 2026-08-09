# 2026-08-09 | Merge de sesiones ejecutor y planificador a `main`

## Resultado

Se integraron en `main` todas las sesiones de esta ronda de ejecutor y planificador. Cada rama
se mantuvo separada durante el trabajo y se incorporo mediante merge explicito.

## Ramas integradas

- `spec/09-admin-source-preview` (`9f171d8`): implementacion del preview de fuente original.
- `spec/10-architecture-explorer` (`8c2a91f`): explorador de arquitectura offline.
- `spec/11-conversational-ux` (`ab8eb26`): catalogo UX conversacional aplicado.
- `spec/09-pdf-modal-requirement` (`e48a99f`): requisito de modal PDF directo.
- `spec/11-open-listening-audio-parity` (`af5e61b`): correccion documental de escucha abierta y
  paridad audio-texto.
- `fix/admin-pdf-modal` (`fe2b11b`): correccion runtime de modal, Blob URL y headers PDF para
  Chrome.

## Verificacion

- Los merges se realizaron en `main` con commits de merge separados.
- Se conservaron las tres entradas de cambios PDF/UX en la bitacora.
- Se preservo el cambio local no comprometido de `AGENTS.md`.
- El smoke visual del navegador queda `MANUAL_PENDING` porque el navegador in-app no estuvo
  disponible durante la validacion.
