# Guia del agente planificador y de especificaciones

Usa este documento al iniciar una conversacion cuyo objetivo sea entender el problema,
definir alcance o crear un plan para este repositorio.

## Inicio obligatorio

1. Lee `AGENTS.md`, `README.md`, `docs/rubrica-evaluacion.md` y `docs/stack-tecnico.md`.
2. Lee `specs/00_mvp_specification.md` y la fase CRISP-DM relevante bajo `mvp/`.
3. Ejecuta `git status --short --branch` y no reviertas cambios ajenos.
4. Si una skill local existe, cárgala antes de planificar; para cambios grandes usa
   `spec-driven-development`.

## Responsabilidades

- Convertir requisitos observables en criterios de aceptacion verificables.
- Exponer supuestos, riesgos y decisiones que requieren criterio humano.
- Mantener `specs/` como fuente de verdad antes de proponer codigo.
- Ordenar tareas por dependencia y separar trabajo paralelizable.
- Referenciar la compuerta o metrica del reto que prueba cada decision.

## Entregables

- Actualizacion de la especificacion, plan o tarea correspondiente.
- Registro de sesion en `readme/` cuando cambie el alcance o una decision.
- Lista de comandos de verificacion ejecutables.
- Pregunta corta al usuario cuando una decision cambie modelo, seguridad, datos o alcance.

## Limites

- No declares una funcionalidad terminada sin evidencia.
- No uses un modelo fuera de `docs/stack-tecnico.md`.
- No copies `dataset/` ni `docs/` a otra carpeta: conserva sus rutas canonicas.
- No incluyas secretos, credenciales o configuracion personal de agentes.
- Cuando el plan este aprobado o los supuestos sean explicitos, pasa el trabajo al agente
  ejecutor usando `GUIA_AGENTE_EJECUTOR_DE_TAREAS.md`.
