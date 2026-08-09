# Entregable 02 - Arquitectura

Manifiesto de la vista de arquitectura. La vista formal derivada vive en
[`architecture.md`](architecture.md); la vista publicada sigue siendo
[`docs/arquitectura.md`](../../../docs/arquitectura.md) y la fuente normativa es la
[spec 06](../../../specs/06_system_flow_diagram_specification.md). No se copia ninguno de
esos documentos en esta ruta.

| Campo | Valor |
|---|---|
| `artifact` | Vista de arquitectura y flujo de decision |
| `source` | [`specs/06_system_flow_diagram_specification.md`](../../../specs/06_system_flow_diagram_specification.md) |
| `derived_view` | [`architecture.md`](architecture.md) |
| `spec_version` | `0.2.0` |
| `published_view` | [`docs/arquitectura.md`](../../../docs/arquitectura.md) |
| `generated_at` | 2026-08-08 |
| `commit` | `working tree/no commit` |
| `status` | `IMPLEMENTED`; preflight local `TESTED`; evidencia manual `MANUAL_PENDING` |

## Declaracion de estado

- `IMPLEMENTED`: FastAPI local, SQLite/FTS5, RAG lexical con filtro
  `status='available' AND enabled=1`, preview textual, enable/disable, delete con snapshots y
  timeout publico estan implementados en la raiz.
- `TESTED`: las pruebas locales cubren lifecycle admin, RAG, eventos, `client_turn_id`,
  `listen_id`, `late_transcript` y `/health`.
- `MANUAL_PENDING`: voz real en navegador, cronometraje G2, proveedor Groq/Whisper real y G5
  con documento externo.
- `PROPOSED`: OCR automatico, video y costo con precios vivos.
- `OUT_OF_SCOPE`: telefonia real, autenticacion empresarial y streaming full-duplex.

El archivo [`architecture.md`](architecture.md) contiene la vista formal derivada, sus enlaces de
codigo/pruebas y las divergencias. Este manifiesto no afirma que la evidencia manual o los gates
pendientes esten aprobados.

## Modelo declarado

`llama-3.1-8b-instant` via Groq, familia Meta Llama permitida; `whisper-large-v3` es STT
opcional y `SpeechSynthesis` del navegador es el TTS principal. La justificacion canonica esta
en el [README raiz](../../../README.md#modelo-permitido).
