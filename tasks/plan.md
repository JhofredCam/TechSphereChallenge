# Plan: Migracion RAG de produccion

## Addendum: prevencion de 409 por timeout de voz (`CALL-VOICE-026`)

Este addendum pertenece a la rama `spec/voice-timeout-final-race`. El diagnostico confirma que
un callback final continuo despues de 30000 ms enviaba `final` y `/turns` en paralelo; el backend
marcaba el intento como `LISTEN_TIMEOUT` y ambos requests devolvian `409`.

### Orden de implementacion

1. **Contrato:** documentar que el backend mantiene `late_transcript` para clientes tardios y
   que el cliente continuo debe cortar antes de emitir `final`.
2. **Guarda frontend:** agregar una transicion idempotente a timeout en el callback `onFinal` del
   modo continuo; registrar solo `timeout`, mostrar reintento y no llamar `/turns`.
3. **Regresion:** cubrir el contrato JavaScript y mantener las pruebas de timeout/backend.
4. **Verificacion:** ejecutar pruebas enfocadas, suite completa, Node, Ruff y diff check; anotar
   el smoke manual pendiente en la bitacora.
5. **Cierre:** actualizar spec/tareas/bitacora, commit, push de rama, merge y push de `main`.

### Riesgos y checkpoints

- Riesgo: duplicar la logica de timeout entre `voice-loop.js` y `app.js`; mitigacion: la guarda
  vive en el limite que recibe `onFinal` y delega el registro a `registerVoiceEvent`.
- Riesgo: aceptar inadvertidamente resultados tardios; mitigacion: no cambiar `CallService` ni
  sus pruebas `409 late_transcript`.
- Checkpoint: el contrato estatico debe confirmar que `sendTurn` aparece despues de la guarda.

Estado del addendum `CALL-VOICE-026`: implementado; falta ejecutar el cierre de verificacion
completa y la integracion de la rama segun la politica de la bitacora.

Estado del addendum `AGENT-RECOVERY-025`: implementado; queda ejecutar el cierre de
verificacion completa y la integracion de la rama segun la politica de la bitacora.

## Addendum: recuperacion de respuesta del agente (`AGENT-RECOVERY-025`)

Este addendum pertenece a la rama `spec/agent-response-recovery` y no cambia el plan de la
migracion RAG. La causa observada fue que `.env` no llegaba al proceso, mientras el agente
ocultaba el modo fallback detrás de una respuesta segura.

### Orden de implementacion

1. **Configuracion:** agregar parser local redacted, precedencia del entorno y campos LLM en
   `Settings`, manteniendo `Settings(...)` explícito aislado para tests.
2. **Inyeccion:** pasar la configuracion cargada al agente y al servicio Whisper opcional; no
   exponer la clave ni cambiar la familia Meta Llama.
3. **Diagnostico:** ampliar `/health` con estado booleano del proveedor y enriquecer el resultado
   seguro del agente sin filtrar errores remotos.
4. **Pruebas:** cubrir parser, precedencia, fallback no vacio, health redacted y regresion HTTP;
   ejecutar primero pruebas enfocadas y después la suite completa.
5. **Evidencia:** actualizar la bitácora, revisar diff/secretos, commit convencional y push de la
   rama dedicada.

### Riesgos y checkpoints

- Riesgo: cargar `.env` durante tests podría activar red; mitigación: solo el `create_app()` por
  defecto carga el archivo, mientras los tests inyectan `Settings` explícito.
- Riesgo: mostrar diagnósticos internos al paciente; mitigación: health solo redacted y copy
  existente para fallback.
- Checkpoint: tests de config/agente/API verdes antes de editar documentación final.

**Spec integradora:** [`specs/19_rag_production_migration_specification.md`](../specs/19_rag_production_migration_specification.md)  
**Fecha:** 2026-08-08  
**Estado:** plan de implementacion, pendiente de ejecucion por el agente ejecutor

## Objetivo

Migrar el recuperador FTS5 del MVP a un pipeline RAG configurable con ChromaDB, embeddings
evaluados, LangChain como orquestador controlado y LangSmith como observabilidad opcional. La
migracion debe preservar SQLite como autoridad, FTS5 como fallback, las citas, el triaje, la
prueba de conocimiento vivo y el contrato de voz. El cierre agrega un logger propio y una
bateria fail-detect que permita conciliar errores, estados, metricas y pruebas sin depender de
la consola ni de mocks que oculten regresiones.

## Decisiones de arquitectura

1. SQLite conserva documentos, paginas, chunks, `enabled`, `corpus_revision`, fuentes, snapshots,
   auditoria y estados de sincronizacion.
2. ChromaDB es un indice derivado, persistente y versionado por chunker, embedding, dimension,
   metrica y revision del corpus.
3. `RagService` es el limite estable. Los objetos Chroma/LangChain no cruzan la API publica.
4. FTS5 sigue siendo baseline, fallback y destino de rollback.
5. El ganador de chunker/embedding se decide por qrels, context precision, recall, citas y
   latencias P50/P95; BGE-M3 y E5-small son hipotesis, no decisiones finales.
6. LangChain no gobierna triaje, elegibilidad, citas, delete ni seguridad de salida.
7. LangSmith captura metadata redacted y nunca es dependencia del camino critico.
8. El perfil local no descarga modelos ni exige red; production puede exigir modelos precargados y
   Chroma server con seguridad adicional.

## Grafo de dependencias

```text
13 configuracion/.env.example
        |
        +--> 14 Chroma/VectorStore <----- 03 ingestion / 04 admin
        |          |
        |          +--> 18 operaciones, rollout, rollback
        |
        +--> 15 benchmark chunking/embeddings
        |          |
        |          +--> 16 LangChain/prompt
        |
        +--> 17 LangSmith/observabilidad
                   |
                   +--> 06 diagrama integrador revisado
                               |
                               +--> 07 pruebas revisadas
                                           |
                                           +--> 23 logger propio y trazabilidad
                                                       |
                                                       +--> 24 suite fail-detect
                                                                   |
                                                                   +--> 06/07, README, mvp/CRISP-DM, informe y demo
```

## Orden de ejecucion

### Fase A: contratos sin cambiar comportamiento

1. Fijar nombres, defaults y validacion de entorno.
2. Extraer protocolos `VectorStore`, `EmbeddingProvider`, `DocumentLoader` y manifest.
3. Mantener FTS5 funcionando con el DTO `SearchResult` actual.
4. Agregar pruebas de paridad y de no regresion.

**Checkpoint A:** suite baseline pasa sin credenciales, red ni modelos descargados.

### Fase B: indice derivado y ciclo documental

1. Persistir metadata de indice y estado de sincronizacion.
2. Construir Chroma por version con IDs/metadata deterministas.
3. Implementar dual-write, reconciliacion y filtro SQLite autoritativo.
4. Cubrir reinicio, disable, enable, delete, fallos parciales y stale vectors.

**Checkpoint B:** upload/search/disable/enable/delete funciona sin reinicio y sin fugas; FTS5
continua disponible.

### Fase C: experimento de calidad y latencia

1. Congelar snapshot de corpus y preparar queries/qrels sin PII.
2. Ejecutar matriz de chunkers/providers/modelos con warmup y repeticiones.
3. Comparar calidad, abstencion, citas, memoria y latencias.
4. Aprobar candidato por gates y documentar descartes.

**Checkpoint C:** existe un reporte reproducible y el candidato supera los umbrales o queda
explicitamente rechazado.

### Fase D: orquestacion y prompt

1. Convertir paginas/chunks a `Document` sin perder metadata.
2. Ensamblar runnables visibles y prompt versionado.
3. Integrar con `AgentService` sin romper aliases, triaje, fallback o copy.
4. Medir overhead de LangChain y fijar limites de contexto.

**Checkpoint D:** una respuesta grounded, una abstencion y una inyeccion pasan las pruebas con
proveedor falso y el camino real conserva fallback.

### Fase E: observabilidad y operacion

1. Implementar el logger propio, contexto, schema, redaction y sinks JSONL/consola.
2. Instrumentar spans por nodo, eventos locales, API, llamada, VAD, audio y RAG.
3. Integrar LangSmith con redaccion, sample rate y fail-open sobre el logger propio.
4. Crear manifest, promotion, canary, rollback y backup/restore.
5. Actualizar diagrama, README, CRISP-DM, metricas e informe.

**Checkpoint E:** rollback a FTS5/version anterior es ejecutable, las trazas no contienen contenido
prohibido y las metricas se pueden contrastar con JSONL.

### Fase F: testing fail-detect

1. Ejecutar unitarias de logger, transformadores, VAD, RAG, triaje, metricas y render contracts.
2. Ejecutar integraciones de llamada, admin/RAG, audio/VAD, datos, logs y `/api/metrics`.
3. Aplicar cobertura por ramas >=80%, Ruff, Node check y validacion del dataset.
4. Registrar P0/P1, pendientes manuales y resultados reproducibles.

### Fase G: evidencia de gates

1. Ejecutar setup limpio y cronometrar G2.
2. Verificar modelo LLM real y familia G3.
3. Ejecutar smoke G4 en navegador con microfono y audio.
4. Ejecutar G5 con documento externo al corpus y delete sin reinicio.
5. Registrar fecha, commit, configuracion redacted, logs y artefactos.

## Trabajo paralelizable

| Frente | Puede iniciar despues de | No debe editar simultaneamente |
|---|---|---|
| Parser de configuracion | contrato 13 | `app/config.py` con otro frente |
| Adaptador Chroma | protocolos 14 | `app/services/rag.py` con integracion |
| Dataset/qrels | limites 15 | corpus canonico o `docs/` |
| LangChain/prompt | DTO estable y benchmark inicial | `agent.py` con otro cambio |
| Redaction/LangSmith | nombres de spans 17 | `metrics.py` sin contrato |
| Logger propio | contrato de `specs/23` | `app/services/logger.py`, `config.py` y sinks sin esquema |
| Suite fail-detect | contrato de `specs/24` y logger estable | fixtures o archivos de servicios sin ownership |
| Runbook/backup | manifest y promotion 18 | README operativo final |
| Tests por frente | contrato de cada frente | fixtures compartidos sin acuerdo |

El agente integrador resuelve conflictos, actualiza `specs/06` y `specs/07`, ejecuta la suite
completa y es responsable de la evidencia final.

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| descarga/cold start de embeddings | G2 y P95 | modelos precargados, perfil FTS5 y medicion separada |
| inconsistencia SQLite-Chroma | fuga o cita stale | SQLite primero, hydration, outbox y reconciliacion |
| score Chroma mal calibrado | abstencion falsa o contexto generico | conversion explicita y benchmark por variante |
| splitter cambia offsets | citas rotas | version de chunker e IDs, no mezclar colecciones |
| LangSmith captura PII | incidente de privacidad | capture false, redaction tests y fail-open |
| LangChain agrega overhead | latencia de voz | nodos visibles, budgets, benchmark con/sin framework |
| eliminar FTS5 demasiado pronto | rollback imposible | conservar dual-read hasta cierre |
| benchmark usa labels prohibidos | resultado invalido | qrels separados, validacion de no-fuga |
| varios workers embedded | corrupcion/lock | un worker o Chroma server probado |
| G5 solo local | gate no demostrado | recorrido manual con documento externo |

## Checkpoints de verificacion

| Checkpoint | Comandos minimos | Criterio de salida |
|---|---|---|
| A | `python -m pytest -q --basetemp <temp>` | baseline verde y sin red |
| B | tests vector/live/admin + reinicio | cero fugas y contrato estable |
| C | `scripts.benchmark_rag.py --gate` | reporte con calidad/latencia y decision |
| D | tests chain/prompt/agent | grounded, abstencion, injection y triage seguros |
| E | observability/ops + rollback | redaction, fail-open y rollback verificables |
| F | `pytest`, cobertura, Ruff y Node check | regresiones P0/P1 detectadas y evidencia local reproducible |
| G | setup, navegador y documento externo | estados G2-G5 honestos y artefactos guardados |

## Criterio de cierre

La migracion no se considera terminada por instalar ChromaDB. Debe existir:

- contrato de configuracion y `.env.example` completo;
- indice Chroma versionado, persistente y reconciliable;
- benchmark reproducible con decision justificada;
- LangChain visible y prompt seguro;
- LangSmith redacted y no bloqueante;
- logger propio con JSONL, niveles, correlacion, stack traces redacted y fail-open;
- rollback y FTS5 funcionales;
- suite fail-detect con cobertura, oraculos de estado y pruebas P0/P1 verdes, mas evidencia
  manual de los gates correspondientes;
- README, diagrama, CRISP-DM, metricas e informe sincronizados con el commit evaluado.
