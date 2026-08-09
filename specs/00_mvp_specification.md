# Especificacion del MVP de seguimiento postoperatorio

## Objetivo

Construir un agente de seguimiento postoperatorio en espanol para pacientes colombianos.
El MVP debe poder levantarse localmente en menos de 15 minutos, contestar con conocimiento
clinico recuperado del corpus, conservar trazabilidad de las fuentes, escalar situaciones de
riesgo y ofrecer dos superficies observables:

1. Consola administrativa para subir, listar y eliminar documentos.
2. Interfaz de llamada en el navegador con microfono y audio del agente.

El MVP no incluye telefonia real, integracion hospitalaria, autenticacion empresarial ni
cobertura clinica universal. Los datos del reto son sinteticos y no validados para uso
asistencial.

### Supuestos explicitos

1. La primera entrega es una aplicacion web monolitica local, no una plataforma distribuida.
2. El navegador Chrome o Edge aporta `SpeechRecognition` para entrada de voz y
   `SpeechSynthesis` para salida; la API tambien acepta texto y audio transcrito por Groq.
3. El modelo de razonamiento principal es `llama-3.1-8b-instant` de Meta servido por Groq,
   una familia permitida por el reto. Si el proveedor no esta disponible, el MVP conserva un
   modo extractivo determinista sustentado en FTS5 para no bloquear pruebas locales; ese modo
   no reemplaza la verificacion de G3 con el modelo declarado.
4. La recuperacion lexical con SQLite FTS5 es suficiente para el camino critico de 24 horas;
   embeddings BGE-M3 quedan como evolucion posterior, no como requisito de arranque.
5. Una alerta persistente en la base local y visible en el resumen satisface el canal de
   escalamiento del MVP; no se envia SMS, correo ni notificacion hospitalaria.
6. El OCR del PDF escaneado se marca explicitamente como pendiente (`needs_ocr`) y no se
   presenta como disponible hasta que exista texto extraible.
7. No se moveran `dataset/` ni `docs/`: siguen siendo las copias canonicas del reto; el
   README previo se conserva en `readme/01_repositorio_base_pre_fork/`.

### Especificaciones derivadas de la siguiente iteracion

Las siguientes specs amplian la organizacion y los contratos sin declarar que ya esten
implementados:

1. [Estructura de entregables bajo `mvp/`](03_mvp_structure_specification.md): define
   `mvp/crisp-dm/` y `mvp/deliverables/`, preservando `dataset/` y `docs/`.
2. [Ciclo documental de `/admin`](04_admin_document_lifecycle_specification.md): agrega
   preview y publicacion independiente del delete.
3. [Timeout configurable de escucha](05_patient_listening_timeout_specification.md): define
   `PATIENT_LISTEN_TIMEOUT_MS` y sus limites de seguridad.
4. [Diagrama normativo del flujo](06_system_flow_diagram_specification.md): depende de las
   tres anteriores y es la fuente de los bloques y subflujos futuros.
5. [Pruebas unitarias e integracion](07_testing_unit_integration_specification.md): define la
   piramide, fixtures, contratos, cobertura y frontera entre automatizacion y evidencia manual.

El orden obligatorio es estructura, admin, timeout y finalmente diagrama. Un cambio en cualquiera
de las tres primeras obliga a revisar la spec del diagrama y la estrategia de pruebas antes de
escribir codigo.

## Stack y modelo

- Python 3.11 o superior.
- FastAPI y Uvicorn para API y archivos estaticos.
- SQLite con FTS5 para persistencia, busqueda y eliminacion atomica de conocimiento.
- PyMuPDF para extraccion por pagina de PDFs.
- openpyxl para validacion reproducible de los cuatro XLSX.
- HTML, CSS y JavaScript sin bundler para minimizar el tiempo de arranque.
- `httpx` para el adaptador OpenAI-compatible de Groq.
- Entrada de voz del navegador con idioma `es-CO`; salida con `SpeechSynthesis`.
- Modelo declarado: `llama-3.1-8b-instant` via Groq, familia Meta Llama permitida.
- STT remoto opcional: `whisper-large-v3` via Groq; no es el modelo de razonamiento.

## Comandos

Los comandos definitivos deben mantenerse sincronizados con `README.md` y con los archivos
de configuracion. El camino previsto es:

```text
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.bootstrap
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m pytest -q
python -m pytest tests/test_live_knowledge.py -q
python -m scripts.validate_dataset
```

La clave `GROQ_API_KEY` es opcional para pruebas locales, pero se recomienda para la demo
completa. No se descargan modelos ni datos durante el bootstrap.

## Estructura del proyecto

```text
app/
  config.py                 Configuracion de entorno y rutas locales.
  database.py               Esquema SQLite, transacciones y consultas base.
  main.py                   Fabrica FastAPI, rutas y archivos estaticos.
  schemas.py                Contratos Pydantic de API y resultados internos.
  services/
    documents.py            Ciclo de vida upload/process/delete.
    ingestion.py            PDFs, TXT/MD y chunks trazables por pagina.
    rag.py                  Recuperacion FTS5 y citas.
    agent.py                Respuesta fundamentada y adaptador LLM.
    triage.py               Reglas conservadoras y no degradacion de nivel.
    calls.py                Turnos, resumen y persistencia de llamadas.
    metrics.py              Logs JSONL y agregacion de latencias/consumo.
  web/                      Consola administrativa e interfaz de llamada.
scripts/
  validate_dataset.py       Contratos XLSX, joins y trampas documentadas.
tests/                      Pruebas unitarias e integracion HTTP.
specs/                      Especificacion viva, plan y tareas.
mvp/                        Fases CRISP-DM en orden.
readme/                     Guia operativa, evidencia y memoria de sesiones.
data/                       Estado local ignorado por Git.
```

## Estilo de codigo

Se usan nombres en `snake_case` para Python, tipos explicitos en los limites, funciones
pequenas y errores convertidos a respuestas HTTP comprensibles. La logica de seguridad
clinica no depende de la salida del modelo.

```python
def classify_triage(text: str, previous_level: str | None = None) -> TriageResult:
    normalized_text = normalize_patient_text(text)
    triggers = find_alarm_triggers(normalized_text)
    level = highest_level(triggers, previous_level)
    return TriageResult(level=level, triggers=triggers, needs_clarification=level == "unknown")
```

Las respuestas del agente deben ser breves, empaticas, en espanol, sin dosis ni diagnosticos
inventados. Todo dato clinico recuperado se delimita como contexto no ejecutable y conserva
documento, pagina, chunk y puntuacion.

## Estrategia de pruebas

- Unitarias: normalizacion, FTS5, chunking, extraccion de PDF, reglas de triaje y contratos
  XLSX.
- Integracion: upload/list/delete, recuperacion antes y despues de borrar, llamadas,
  resumen y metricas.
- Smoke manual: `/admin` muestra `available`; `/call` solicita microfono y reproduce una
  respuesta en espanol.
- Datos: validar hoja `result`, encabezados, filas esperadas, JSON embebido, joins por
  `paciente_id` y `caso_id = "caso_" + trayectoria_id`.
- Comp puertas: documentar G2, G3, G4 y G5 con comandos y evidencia; G1 queda como checklist
  de entrega del informe y video.
- Cobertura objetivo del codigo propio: 80% en servicios criticos; si el tiempo limita la
  cobertura, no se omiten las pruebas de borrado, abstencion y falso negativo.

## Limites de trabajo

- **Siempre:** validar entradas, usar consultas parametrizadas, registrar fuentes y metricas,
  ejecutar pruebas enfocadas antes de cerrar, no usar `label_ground_truth` como contexto del
  paciente.
- **Preguntar antes:** cambiar el modelo o proveedor declarado, incorporar una base externa,
  mover `dataset/` o `docs/`, introducir autenticacion, modificar el esquema persistido de
  manera incompatible o agregar un servicio obligatorio.
- **Nunca:** commitear secretos, afirmar que un PDF escaneado esta disponible sin OCR, citar un
  documento eliminado en una respuesta nueva, inventar dosis/diagnosticos, mezclar capas del
  dataset, usar un modelo fuera de las familias permitidas o ignorar pruebas fallidas.

## Criterios de exito

1. `python -m app.bootstrap` crea la base, valida el dataset y procesa recursivamente el
   corpus sin descargar nada; rutas con espacios y el PDF escaneado quedan registradas.
2. La consola permite subir un PDF/TXT/MD nuevo, muestra `available` o `needs_ocr`, lista el
   documento y lo elimina.
3. Una frase unica de un documento subido es recuperable con fuente y pagina, y deja de ser
   recuperable despues de eliminar el documento sin reiniciar el servidor.
4. La interfaz de llamada inicia una llamada, recibe voz por microfono en Chrome/Edge,
   muestra la transcripcion, responde y reproduce audio; el texto sigue disponible como
   fallback auditable.
5. Una pregunta sin evidencia produce abstencion explicita y no una respuesta clinica
   inventada.
6. Senales rojas nunca se degradan a verde; las amarillas generan alerta persistente y las
   ambiguas piden aclaracion.
7. Al cerrar una llamada se guarda un resumen con paciente, procedimiento, sintomas,
   decision, fuentes, alerta y proximos pasos.
8. Los logs y `/api/metrics` exponen P50/P95 de latencia, tokens de entrada/salida, llamadas
   al modelo, consultas RAG y formula de costo documentada.
9. El README principal permite levantar el sistema en un entorno limpio en 15 minutos o menos.

## Preguntas abiertas y decisiones notificadas

- El ID de Groq puede retirarse; antes de una demo se debe verificar el sucesor vigente dentro
  de Meta Llama y actualizar modelo, informe y `.env.example` juntos.
- La primera version no hace OCR automatico. La decision de incorporar Tesseract/OCR remoto
  requiere criterio porque agrega instalacion y un nuevo riesgo de reproducibilidad.
- La voz es turn-taking del navegador, no streaming full-duplex. Barge-in y WebRTC quedan
  fuera del corte de 24 horas salvo que la prueba manual revele que la evaluacion lo exige.
- El canal de alerta es la consola/base local. Un canal externo solo se incorpora con
  credenciales y un flujo de prueba independiente.
- La preview, el enable/disable de documentos y el timeout configurable estan especificados
  para el siguiente corte; no se consideran criterios cumplidos en el baseline actual hasta
  tener codigo y evidencia.
