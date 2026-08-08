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

## Arranque

```text
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir:

- `http://127.0.0.1:8000/admin` para gestionar documentos.
- `http://127.0.0.1:8000/call` para la llamada browser/API.

Si se usa Groq, definir `GROQ_API_KEY` en el entorno antes de arrancar. No escribir claves en
Git ni en capturas.

## Preflight

Antes de la demo, ejecutar:

```text
python -m pytest -q --basetemp <temp>
ruff check .
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>
```

Resultados del 2026-08-08: 38 tests pasaron, Ruff no reporto hallazgos, el dataset fue
validado como `3991/40/40/160` y el bootstrap proceso 104 documentos con estados
`available=103` y `needs_ocr=1`. La prueba de idempotencia paso dentro de la suite. El
recorrido de conocimiento vivo local tambien esta cubierto por las pruebas, pero G5 aun
requiere una demostracion con documento externo al corpus.

## Criterio de 15 minutos

Cronometrar desde `python -m venv .venv` hasta que `/admin` y `/call` respondan. Anotar
version de Python, commit, navegador, hora de inicio/fin y cualquier espera de credenciales
en [metricas y evidencia](04_metricas_y_evidencia.md). El resultado actual es `PENDIENTE`:
el bootstrap y los tests locales no sustituyen el cronometraje G2 desde un entorno limpio.
