# Vista formal de arquitectura

Esta vista es un artefacto derivado, no una segunda autoria del diagrama. La vista normativa y
detallada es [`specs/06_system_flow_diagram_specification.md`](../../../specs/06_system_flow_diagram_specification.md);
la vista publicada de implementacion es [`docs/arquitectura.md`](../../../docs/arquitectura.md).

## Procedencia

| Campo | Valor |
|---|---|
| `artifact` | Vista formal derivada de arquitectura y flujo |
| `source` | [`specs/06_system_flow_diagram_specification.md`](../../../specs/06_system_flow_diagram_specification.md) |
| `spec_version` | `0.3.0` |
| `generated_at` | `2026-08-08` |
| `commit` | `working tree/no commit` |
| `published_view` | [`docs/arquitectura.md`](../../../docs/arquitectura.md) |
| `status` | `IMPLEMENTED`; preflight local `TESTED`; evidencia manual `MANUAL_PENDING` |

## Alcance de la vista

El runtime es un monolito FastAPI/Uvicorn con SQLite/FTS5, archivos locales y dos superficies
browser. El flujo detallado, IDs estables, relaciones y matriz `TRZ-*` no se duplican aqui. Este
artefacto resume contratos y procedencia para el entregable formal.

```text
Administrador -> /admin -> DocumentService -> ingestion -> SQLite/FTS5
                                  | preview / enabled / delete + snapshots
Paciente -> /call -> CallService -> triaje -> RAG(available AND enabled=1)
                                      |                 |
                                      +-> AgentService -+-> respuesta/abstencion
                                             | fallback FTS5 / Groq opcional
                                      browser SpeechSynthesis es-CO
                                      SQLite + events.jsonl + /api/metrics
```

Contratos relacionados: `GET/POST/PATCH/DELETE /api/admin/documents`,
`GET .../preview`, `POST /api/calls`, `POST .../turns`, `POST .../audio`,
`POST .../voice-events`, `POST .../voice-timing`, `POST .../finish`, `GET /health` y
`GET /api/metrics`. Sus estados y trazabilidad normativa estan en la [spec 06](../../../specs/06_system_flow_diagram_specification.md#mapa-de-contratos-y-submodulos).

La spec 06 version `0.3.0` agrega una convencion visual para distinguir usuario, admin, bot, RAG,
datos, externos, seguridad y metricas. Las propuestas de inventario responsive sin SHA visible y
de archivo original en modal estan en [spec 08](../../../specs/08_admin_inventory_ux_specification.md)
y [spec 09](../../../specs/09_admin_source_preview_specification.md); ambas siguen
`PROPOSED` y no alteran el estado del runtime resumido aqui.
La futura vista navegable de esa arquitectura esta especificada en [spec 10](../../../specs/10_architecture_explorer_specification.md)
y tambien sigue `PROPOSED`; no es una segunda autoridad del flujo.

## Modelo y proveedor

| Componente | Seleccion | Estado |
|---|---|---|
| Razonamiento | `llama-3.1-8b-instant` via Groq | `TESTED` en allowlist/config; llamada remota `MANUAL_PENDING` |
| Familia | Meta Llama | permitida por [`docs/stack-tecnico.md`](../../../docs/stack-tecnico.md) |
| STT opcional | `whisper-large-v3` via Groq | contrato y fallback `TESTED`; Whisper real `MANUAL_PENDING` |
| TTS | `SpeechSynthesis`, locale `es-CO` | `IMPLEMENTED`; audio real `MANUAL_PENDING` |
| Recuperacion | SQLite FTS5 lexical | `TESTED`; filtro `status='available' AND enabled=1` |

## Estado de capacidades

| Capacidad | Codigo/contrato | Prueba o evidencia | Estado |
|---|---|---|---|
| Estructura de entrega y proceso | `mvp/crisp-dm/`, `mvp/deliverables/` | preflight de rutas y ausencia de copias prohibidas | TESTED |
| Preview textual | `app/services/documents.py`, `GET .../preview`, `app/web/app.js` | `tests/test_admin_lifecycle.py` | TESTED API; UI manual pendiente |
| Inventario responsive y sin SHA visible | spec 08; todavia sin runtime | smoke responsive y DOM futuros | PROPOSED |
| Archivo original en modal | spec 09; endpoint binario futuro | pruebas MIME/bytes y smoke modal futuro | PROPOSED |
| Publicacion independiente | `enabled`, `rag_eligible`, `PATCH .../{id}` | `tests/test_admin_lifecycle.py` | TESTED |
| RAG activo | `app/services/rag.py` | tests admin/live knowledge | TESTED |
| Delete y snapshots | `app/database.py`, `DocumentService.delete`, `sources` | `tests/test_admin_lifecycle.py`, `tests/test_live_knowledge.py` | TESTED local; G5 externo pendiente |
| Timeout total por turno | `Settings`, `/health`, `app/web/app.js` | `tests/test_timeout.py` | TESTED API; Chrome/Edge pendiente |
| Estados de escucha e IDs | `listening_attempts`, `client_turn_id`, `listen_id` | `tests/test_timeout.py` | TESTED API; voz real pendiente |
| Eventos de voz | `POST /api/calls/{id}/voice-events`, JSONL | `tests/test_timeout.py` | TESTED API |
| Voz browser y audio | `SpeechRecognition`, `SpeechSynthesis` | `node --check`; smoke manual | IMPLEMENTED; MANUAL_PENDING |
| Costo con precios vivos | agregador/formula documental | falta precio y log real | PROPOSED |
| OCR automatico | no existe en runtime; `needs_ocr` si existe | no aplica | PROPOSED |
| Video de entrega | `mvp/deliverables/04_video/README.md` | no hay video/URL | PROPOSED |
| Auth, CSRF y streaming full-duplex | fuera del contrato local | no aplica | OUT_OF_SCOPE |

## Divergencias

| ID | Diferencia | Fuente responsable | Estado |
|---|---|---|---|
| `DIVERGENCE-001` | el proceso prescribe bind `127.0.0.1`, pero `app.main` no impone por codigo un bind local si Uvicorn se lanza con otros flags | spec 04 y runtime/security | pendiente explicito; no se oculta como propuesta |
| `DIVERGENCE-002` | la spec 07 concurrente conserva catalogos que llaman futuras a algunas suites 04/05 ya implementadas | [`specs/07_testing_unit_integration_specification.md`](../../../specs/07_testing_unit_integration_specification.md) | se conserva sin editar; la evidencia de esta vista apunta a los tests ejecutados |
| `DIVERGENCE-003` | no hay runner browser automatizado ni credencial de proveedor en esta verificacion | `app/web/`, spec 07 y rubrica | `MANUAL_PENDING`; no aprueba G4/G5/G3 real |

## Evidencia local

| Comando | Resultado |
|---|---|
| `python -m pytest tests/test_admin_lifecycle.py tests/test_timeout.py -q --basetemp <temp>` | `24 passed` |
| `python -m pytest -q --basetemp <temp>` | `96 passed` |
| `ruff check .` | `All checks passed` |
| `node --check app/web/app.js` | valido |
| `python -m scripts.validate_dataset` | valido; `3991/40/40/160` |
| `python -m app.bootstrap --data-dir <temp>` | `104` documentos; `103 available`, `1 needs_ocr` |

Estas pruebas no miden cronometraje G2, microfono/audio G4, documento externo G5 ni Groq/Whisper
real. Esos gates y metricas de voz/costo siguen `MANUAL_PENDING` o `PENDIENTE` en el informe.

## Enlaces de implementacion y pruebas

- Runtime/API: [`app/main.py`](../../../app/main.py), [`app/config.py`](../../../app/config.py),
  [`app/database.py`](../../../app/database.py).
- Servicios: [`app/services/documents.py`](../../../app/services/documents.py),
  [`app/services/rag.py`](../../../app/services/rag.py), [`app/services/calls.py`](../../../app/services/calls.py),
  [`app/services/metrics.py`](../../../app/services/metrics.py), [`app/services/voice.py`](../../../app/services/voice.py).
- Web: [`app/web/admin.html`](../../../app/web/admin.html), [`app/web/call.html`](../../../app/web/call.html),
  [`app/web/app.js`](../../../app/web/app.js).
- Pruebas: [`tests/test_admin_lifecycle.py`](../../../tests/test_admin_lifecycle.py),
  [`tests/test_timeout.py`](../../../tests/test_timeout.py), [`tests/test_api.py`](../../../tests/test_api.py),
  [`tests/test_live_knowledge.py`](../../../tests/test_live_knowledge.py),
  [`tests/test_calls.py`](../../../tests/test_calls.py), [`tests/test_metrics.py`](../../../tests/test_metrics.py).
