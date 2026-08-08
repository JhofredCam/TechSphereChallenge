# Guia del agente ejecutor de tareas

Usa este documento al iniciar una conversacion cuyo objetivo sea implementar, probar o
documentar una tarea ya definida.

## Inicio obligatorio

1. Lee `AGENTS.md`, `README.md`, `specs/00_mvp_specification.md`,
   `specs/02_implementation_tasks.md` y la fase `mvp/` relacionada.
2. Ejecuta `git status --short --branch`, `git diff --stat` y revisa los cambios ajenos antes
   de editar.
3. Carga `spec-driven-development` para cambios de varias piezas y `git-commit` cuando el
   usuario solicite cierre o commit.
4. Confirma que la tarea tiene aceptacion y comando de verificacion; si no, vuelve al agente
   planificador.

## Flujo de trabajo

1. Implementa el cambio mas pequeno que satisfaga la tarea.
2. Mantén limites de seguridad: entrada validada, consultas parametrizadas, fuentes
   trazables y abstencion cuando falte evidencia.
3. Prueba primero la unidad o integracion enfocada y luego el conjunto completo.
4. Actualiza la especificacion, README o registro de sesion si una decision cambia.
5. Revisa `git diff`, `git status` y secretos antes del cierre.

## Paralelismo seguro

- Divide por carpetas o contratos sin solapamiento.
- No edites a la vez el mismo esquema, endpoint o archivo de documentacion desde dos agentes.
- El agente que integra es responsable de resolver conflictos y ejecutar la prueba final.

## Verificacion minima

- `python -m pytest -q`
- `python -m scripts.validate_dataset`
- Smoke manual de `/admin` y `/call` si la tarea toca superficies web o voz.
- Para conocimiento vivo: subir, consultar, eliminar y consultar de nuevo sin reiniciar.

## Cierre

No uses `git reset --hard`, `git checkout --`, `--force` ni `--no-verify`. Nunca commitees
`.env`, claves, bases locales o logs. Si el usuario pide commit, usa la skill `git-commit`,
analiza el diff real y crea un commit convencional que incluya solo los archivos intencionados.
