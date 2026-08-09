# 2026-08-09 | Recuperacion de respuesta del agente

## Alcance

Se investigó por qué el agente no estaba usando el modelo durante `POST /api/calls/{id}/turns`.
La implementación siguió `GUIA_AGENTE_PLANIFICADOR_Y_ESPECIFICACIONES.md`,
`GUIA_AGENTE_EJECUTOR_DE_TAREAS.md` y la spec
[`AGENT-RECOVERY-025`](../../specs/25_agent_response_recovery_specification.md), en la rama
`spec/agent-response-recovery`.

## Hallazgo y decisión

El archivo `.env` de la raíz tenía una credencial local válida, pero el proceso Python no la
recibía porque `Settings.from_env()` solo consultaba `os.environ`. El agente entonces usaba el
fallback extractivo; además, el estado del proveedor no era visible en `/health`.

Se agregó un parser local pequeño y opt-in: solo la instancia por defecto de `app.main:app` lee
`.env`, el entorno del proceso gana y ninguna clave se registra o devuelve. La configuración se
inyecta en Groq y Whisper, `/health` expone solo `llm_configured`, `llm_provider` y `llm_status`,
y el resultado del agente identifica `model_used`, `fallback` o `abstained` sin mostrar errores
remotos al paciente.

## Archivos y verificación

- `app/config.py`, `app/main.py`, `app/services/agent.py`: configuración, inyección y fallback.
- `tests/test_config_contracts.py`, `tests/test_agent.py`, `tests/test_api.py`: regresiones.
- `README.md`, `specs/25_agent_response_recovery_specification.md`, `tasks/` y esta bitácora:
  documentación reproducible.

Comandos ejecutados:

```text
python -m pytest tests/test_config_contracts.py tests/test_agent.py tests/test_api.py -q --basetemp .pytest-tmp/focused-rerun
python -c "from app.config import Settings; s=Settings.from_env(load_dotenv=True); print(bool(s.groq_api_key), s.groq_model)"
python -m pytest -q --basetemp .pytest-tmp/agent-full
ruff check app tests
node --check app/web/app.js
git diff --check
```

La primera suite enfocada pasó 28 pruebas. El smoke remoto se ejecutó sin imprimir la clave ni
el contenido de la respuesta; su resultado queda registrado junto con la verificación final de
la sesión.

## Resultado de smoke

La carga de configuracion reporto `key_present=True` y `model=llama-3.1-8b-instant`; el smoke
remoto respondio con `provider_call=ok`, texto presente y el mismo modelo. El `/health` de la
instancia por defecto reporto `llm_configured=True`, `llm_provider=groq`,
`llm_status=configured` y no incluyo la clave. Ninguna salida registro el token ni el contenido
clinico de la respuesta.

La prueba end-to-end temporal subio una fuente, inicio una llamada y envio el turno por HTTP:
`upload=200`, `turn=200`, `provider=groq`, `model_calls=1`, `source_count=1` y ambos textos no
vacios. El modelo produjo una salida que el guard de citas rechazo, por lo que se aplico el
fallback grounded seguro; esto confirma que un rechazo del modelo tampoco deja al paciente sin
respuesta.

## Riesgos y siguiente acción

Los procesos Uvicorn ya iniciados antes del cambio conservan el grafo anterior: hay que
reiniciarlos y abrir una llamada nueva. Las llamadas antiguas que quedaron en `PROCESSING` no
se deben reutilizar como prueba de la corrección. La voz de navegador sigue dependiendo de
Chrome/Edge y del permiso de micrófono.
