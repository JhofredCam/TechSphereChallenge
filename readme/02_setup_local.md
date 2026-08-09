# Setup local

## Estado

Procedimiento operativo de la [especificacion del MVP](../specs/00_mvp_specification.md).
Al 2026-08-08 el checkout contiene `requirements.txt`, `app/bootstrap.py`, `app/main.py`,
la suite de `tests/` y los scripts de validacion. La ejecucion local esta verificada; G2
requiere aun cronometraje desde un entorno limpio.

## Requisitos

- Python 3.11 o superior.
- Chrome o Edge para probar microfono y `SpeechSynthesis`.
- `GROQ_API_KEY` solo para la ruta remota completa; los tests locales deben poder usar el
  modo extractivo sin secreto.
- Los datos ya estan locales en [`dataset/`](../dataset/); no se descarga ningun dataset.
- `.env.example` incluye `PATIENT_LISTEN_TIMEOUT_MS=30000`. `Settings` valida el valor y el
  runtime lo publica por `/health`; el checkout no carga automaticamente el archivo de ejemplo.
  El timer del navegador usa el valor efectivo, no una lectura directa de `.env`.
- `.env.example` tambien documenta el target de migracion (`CHUNK_SIZE`, `CHUNK_OVERLAP`,
  `SPLITTER_TYPE`, embeddings, Chroma, `TOP_K`, `SIMILARITY_THRESHOLD` y LangSmith). En este
  checkout esas variables nuevas son contrato de plan y no implican que Chroma o LangSmith ya
  esten instalados.

## Instalacion

Ejecutar desde la raiz del repositorio:

```text
python --version
python -m venv .venv
```

En PowerShell:

```text
.venv\Scripts\Activate.ps1
```

En macOS/Linux:

```text
source .venv/bin/activate
```

Continuar en cualquier sistema:

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>
```

El bootstrap crea la base local y procesa recursivamente el corpus sin descargar datos ni
modelos. El 2026-08-08 proceso 104 documentos: 103 quedaron en `available` y 1 en
`needs_ocr`; el PDF sin texto no se convierte silenciosamente en una fuente disponible.
`<temp>` representa un directorio local fuera de las fuentes canonicas, por ejemplo
`data-verification/run-01`.

Para repetir la suite y el lint del repositorio, instalar tambien las herramientas de
desarrollo declaradas en `requirements-dev.txt`:

```text
python -m pip install -r requirements-dev.txt
```

## Operación de índices RAG

El perfil `challenge-local` usa FTS5 y no descarga modelos ni servicios externos. Para validar
un índice versionado en un entorno operativo se usan manifests inmutables, reconciliación y un
puntero activo; las versiones anteriores nunca se borran durante rollback:

```text
python -m scripts.check_rag_config --profile staging --show-effective --redact-secrets
python -m scripts.build_rag_index --index-version <new-version> --profile staging --data-dir <temp>/rag-index
python -m scripts.validate_rag_index --index-version <new-version> --strict --data-dir <temp>/rag-index
python -m scripts.reconcile_rag_index --index-version <new-version> --dry-run --data-dir <temp>/rag-index
python -m scripts.promote_rag_index --index-version <new-version> --reason "canary aprobado" --data-dir <temp>/rag-index
python -m scripts.rag_status --json --redact-secrets --data-dir <temp>/rag-index
```

El build ocurre fuera de la ruta de voz. SQLite sigue siendo la autoridad de elegibilidad y FTS5
es el fallback; Chroma server, múltiples workers y exposición pública requieren controles de
seguridad y operación adicionales.

## Arranque

```text
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir:

- `http://127.0.0.1:8000/admin` para gestionar documentos.
- `http://127.0.0.1:8000/call` para la llamada browser/API.
- `http://127.0.0.1:8000/health` para comprobar backend RAG, modelo, voz, revision y timeout publico.
- `http://127.0.0.1:8000/docs` para OpenAPI.

Si se usa Groq, definir `GROQ_API_KEY` en el entorno antes de arrancar. No escribir claves en
Git ni en capturas.

El timeout de escucha del paciente esta implementado y se documenta en
[`specs/05_patient_listening_timeout_specification.md`](../specs/05_patient_listening_timeout_specification.md).
Es una duracion total por intento, default `30000`, rango `1000..300000`, distinta de Groq
(`12 s`), Whisper (`30 s`) y SQLite (`5000 ms`). Un timeout/no respuesta/parcial no crea turno;
la UI ofrece reintento o texto y un transcript tardio recibe `409 late_transcript`. Las pruebas
locales cubren el contrato; el smoke manual de Chrome/Edge, microfono y audio sigue pendiente.

En `/admin`, el flujo local es: upload -> preview textual -> disable (conserva e indexa pero
excluye de RAG) -> enable (recupera sin reingesta) -> delete (limpia FTS5, conserva snapshot y
retira el archivo). G5 externo sigue pendiente aunque el recorrido local este probado.

El upgrade target agrega perfiles:

- `challenge-local`: FTS5, sin red ni descarga de embeddings; es el perfil que conserva G2 del
  baseline.
- `staging`: Chroma y modelo de embeddings precargados, benchmark, dual-read y LangSmith redacted.
- `production`: indice versionado, reconciliacion, canary, rollback y secret manager; no se
  declara disponible hasta ejecutar el runbook de Specs 14, 17 y 18.

## Preflight

Antes de la demo, ejecutar:

```text
python -m pytest -q --basetemp <temp>
python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>
ruff check .
node --check app/web/app.js
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>
```

Resultados del 2026-08-08: 24 tests enfocados y 96 tests completos pasaron, Ruff no reporto
hallazgos, `node --check app/web/app.js` fue valido, y el dataset fue
validado como `3991/40/40/160` y el bootstrap proceso 104 documentos con estados
`available=103` y `needs_ocr=1`. La prueba de idempotencia paso dentro de la suite. El
recorrido de conocimiento vivo local tambien esta cubierto por las pruebas, pero G5 aun
requiere una demostracion con documento externo al corpus.

## Criterio de 15 minutos

Cronometrar desde `python -m venv .venv` hasta que `/admin` y `/call` respondan. Anotar
version de Python, commit, navegador, hora de inicio/fin y cualquier espera de credenciales
en [metricas y evidencia](04_metricas_y_evidencia.md). El resultado actual es
`MANUAL_PENDING`:
el bootstrap y los tests locales no sustituyen el cronometraje G2 desde un entorno limpio.
