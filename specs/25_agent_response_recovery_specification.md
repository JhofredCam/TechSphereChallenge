# Spec: Recuperacion de respuesta del agente y configuracion LLM local

**ID:** `AGENT-RECOVERY-025`
**Estado:** `IMPLEMENTED`
**Fecha:** 2026-08-09
**Depende de:** [`specs/00_mvp_specification.md`](00_mvp_specification.md),
[`specs/07_testing_unit_integration_specification.md`](07_testing_unit_integration_specification.md),
[`specs/16_rag_langchain_orchestration_specification.md`](16_rag_langchain_orchestration_specification.md)

## Diagnostico y supuestos

La ejecucion local observada no tenia `GROQ_API_KEY` en el entorno del proceso, aunque existia
una clave real en el archivo `.env`. `Settings.from_env()` solo leia `os.environ`, por lo que el
agente entraba en fallback extractivo sin que `/health` ni la interfaz explicaran el modo activo.
Ademas, el adaptador ocultaba el fallo remoto dentro de un fallback seguro; eso evita una
excepcion, pero dificulta saber por que no se uso el modelo.

Supuestos de esta spec:

1. El archivo `.env` en la raiz es una configuracion local intencional para el arranque por
   defecto; nunca se versiona ni se muestra en respuestas, health o logs.
2. Las variables ya exportadas por el proceso tienen precedencia sobre `.env`, para permitir
   despliegues y pruebas reproducibles.
3. Se conserva la familia permitida Meta Llama y el modelo declarado actual; esta spec no cambia
   proveedor, familia ni politica clinica.
4. Si Groq no esta configurado, falla, devuelve una respuesta vacia o produce una salida insegura,
   el paciente debe recibir una respuesta segura no vacia basada en FTS5 o una abstencion clara.
5. `health` es diagnostico publico y solo expone booleanos, estados, proveedor y modelo permitido;
   nunca expone claves, headers, prompts, excepciones remotas ni contenido clinico.

## Objetivo

Hacer que el agente responda de manera observable en `/call` y en `POST /api/calls/{id}/turns`.
Cuando existe una configuracion LLM valida, la aplicacion debe usarla; cuando no existe o no esta
disponible, debe conservar una respuesta segura y dejar visible que esta operando en fallback.

## Tech Stack

- Python 3.11+, FastAPI, Uvicorn y `httpx` existentes.
- Parser `.env` local pequeno, sin agregar una dependencia obligatoria.
- Groq OpenAI-compatible con el modelo Meta Llama ya declarado.
- SQLite/FTS5 como recuperador y fallback local.
- HTML/CSS/JavaScript sin bundler para la interfaz de llamada.

## Commands

```text
python -m pytest tests/test_config_contracts.py tests/test_agent.py tests/test_api.py -q --basetemp .pytest-tmp/agent-recovery
python -m pytest -q --basetemp .pytest-tmp/agent-recovery-full
ruff check app tests
node --check app/web/app.js
git diff --check
```

Smoke opcional con credencial local, sin imprimirla:

```text
python -c "from app.config import Settings; s=Settings.from_env(load_dotenv=True); print(bool(s.groq_api_key), s.groq_model)"
```

## Project Structure

```text
app/config.py                   -> lectura redacted de .env y configuracion LLM.
app/main.py                     -> inyeccion de configuracion y health publico.
app/services/agent.py           -> estado del proveedor y fallback seguro no vacio.
app/services/voice.py           -> reutiliza configuracion para Whisper opcional.
tests/test_config_contracts.py -> precedencia, parser y ausencia de secretos.
tests/test_agent.py             -> fallback y diagnostico del proveedor.
tests/test_api.py               -> health y respuesta HTTP observable.
tasks/plan.md, tasks/todo.md    -> plan y tareas de esta implementacion.
readme/06_bitacora_de_sesiones/ -> evidencia de la sesion.
```

## Code Style

La carga de entorno no muta `os.environ` y no imprime valores sensibles:

```python
values = dict(environ or os.environ)
if load_dotenv and environ is None:
    for key, value in read_local_env(project_root / ".env").items():
        values.setdefault(key, value)
return Settings(groq_api_key=values.get("GROQ_API_KEY"))
```

Se mantienen `snake_case`, tipos explicitos en limites, errores internos redacted y mensajes
patient-facing separados de diagnosticos tecnicos. El resultado de `AgentService.respond()` debe
conservar `patient_text`, `voice_text`, `display_text`, `provider`, `model_calls`, `reason` y
agregar un estado seguro del proveedor sin el texto de la excepcion remota.

## Testing Strategy

- Unitarias: parser de `.env`, precedencia del proceso, comillas, comentarios y ausencia de
  archivos; ninguna prueba debe contactar Groq por accidente.
- Unitarias de agente: clave ausente, proveedor disponible mediante adapter falso, error remoto,
  respuesta vacia y salida insegura; todos dejan texto patient-facing no vacio.
- Integracion HTTP: `health` reporta `llm_configured`, `llm_provider` y `llm_status` sin secretos;
  un turno con provider no configurado responde por fallback y conserva fuentes/triage.
- Regresion: la suite completa, Ruff y Node check pasan; el smoke remoto queda como evidencia
  manual y usa una clave existente sin registrarla.

## Boundaries

- **Always:** dar prioridad al entorno del proceso, cargar `.env` solo para la instancia por
  defecto, redactor health/logs, mantener el fallback seguro, conservar triaje y citas, probar
  sin red ni credenciales.
- **Ask first:** cambiar la familia/modelo permitido, agregar un proveedor obligatorio, cambiar
  el esquema SQLite, hacer que el arranque falle por ausencia de Groq o instalar modelos locales.
- **Never:** commitear `.env` o claves, imprimir tokens/headers, devolver excepciones del proveedor
  al paciente, bloquear toda respuesta si Groq falla, inventar contenido clinico o ocultar la
  diferencia entre modelo remoto y fallback.

## Success Criteria

- **`AGENT-RECOVERY-AC-01`:** la app creada sin `Settings` explícito lee `.env` de la raiz sin
  mutar el proceso; una variable ya exportada gana sobre el archivo.
- **`AGENT-RECOVERY-AC-02`:** `Settings` explícito usado por tests no lee accidentalmente el
  `.env` del proyecto ni realiza llamadas remotas.
- **`AGENT-RECOVERY-AC-03`:** `/health` informa `llm_configured`, `llm_provider`, `llm_status` y
  modelo; no contiene `GROQ_API_KEY` ni su valor.
- **`AGENT-RECOVERY-AC-04`:** con una fuente recuperable y provider no configurado, un turno
  devuelve `200`, `patient_text`/`display_text` no vacíos, `grounded=true` y razón auditable.
- **`AGENT-RECOVERY-AC-05`:** un fallo, timeout, JSON vacío o salida insegura del provider no
  produce una respuesta vacía ni una excepción HTTP 500; usa fallback o abstención segura.
- **`AGENT-RECOVERY-AC-06`:** todas las pruebas existentes siguen pasando y el smoke del modelo
  remoto puede verificar configuración sin revelar la clave.

## Open Questions

1. La disponibilidad futura del identificador exacto de Groq debe revisarse antes de la demo;
   cualquier sucesor debe pertenecer a Meta Llama y actualizar configuración, informe y evidencia.
2. El fallback sigue siendo una garantía de seguridad y pruebas locales; no cuenta como evidencia
   de la compuerta G3 ni reemplaza el smoke remoto/manual.
