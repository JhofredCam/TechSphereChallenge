# Spec: Estructura de entregables bajo `mvp/`

**Estado:** propuesta para revision humana; no aplicada en este checkout
**Version:** 0.1.0
**Fecha:** 2026-08-08

## Objetivo

Definir una reestructuracion del repositorio en la que los cuatro entregables formales del
reto y los artefactos de proceso del MVP vivan bajo `mvp/`. Las seis fases CRISP-DM que hoy
estan directamente dentro de `mvp/` pasaran conceptualmente a `mvp/crisp-dm/`.

Esta spec define ownership, rutas, dependencias y una migracion verificable. No mueve carpetas,
no copia archivos y no modifica codigo en esta sesion.

## Tech Stack

La reestructuracion usa Markdown, enlaces relativos y los comandos del runtime existente. No
agrega framework, dependencia Python, servicio, modelo ni mecanismo de almacenamiento. Git LFS,
releases o URLs externas para el video requieren una decision separada.

## Project Structure

La estructura objetivo completa, ownership y rutas de soporte estan en la seccion
[Estructura objetivo](#estructura-objetivo). El punto importante es que `mvp/` agrupa entrega y
proceso, mientras `app/`, `scripts/`, `tests/`, `specs/`, `readme/`, `.env.example`, `dataset/`,
`docs/` y `data/` conservan responsabilidades distintas.

## Code Style

No se modifica codigo. Las referencias de implementacion deben conservar nombres Python en
`snake_case`, rutas relativas en Markdown y una fuente unica por afirmacion. Un manifiesto debe
preferir campos estables como `source`, `generated_at`, `commit`, `status` y `artifact` en vez
de texto ambiguo o estado inferido.

### Alcance

- Concentrar los entregables formales en `mvp/deliverables/`.
- Reubicar las seis fases en `mvp/crisp-dm/` durante una etapa posterior.
- Mantener una unica fuente de verdad por afirmacion, artefacto y evidencia.
- Preservar los comandos ejecutados desde la raiz y las rutas canonicas del reto.
- Permitir que el diagrama, la administracion documental y el timeout tengan rutas estables
  antes de su implementacion.

### Definiciones

- **Entregable formal:** repositorio, diagrama, informe final y video exigidos por G1.
- **Artefacto CRISP-DM:** documentacion de una de las seis fases del proceso.
- **Fuente canonica del reto:** `dataset/`, `docs/rubrica-evaluacion.md` y
  `docs/stack-tecnico.md`; no se mueven ni se copian.
- **Vista publicada del MVP:** `docs/arquitectura.md` y `docs/informe-final.md`; permanecen como
  vistas del baseline, pero su fuente normativa futura sera la spec o el artefacto que indiquen.
- **Runtime:** codigo y pruebas en `app/`, `scripts/` y `tests/`; no se duplican dentro de
  `mvp/` en esta migracion.
- **Estado generado:** `data/`, con SQLite, uploads y eventos; no es un entregable versionado.
- **Spec normativa:** documento bajo `specs/` que define requisitos antes de escribir codigo.

## Supuestos y decisiones

1. `mvp/` es el contenedor de entrega y proceso, no necesariamente el paquete de importacion
   de Python. El runtime conserva sus rutas de raiz hasta una decision separada.
2. `specs/` permanece en la raiz como fuente de verdad del trabajo spec-driven. No se crea una
   segunda copia de las specs dentro de `mvp/`.
3. `readme/` permanece en la raiz como documentacion operativa y bitacora, porque la guia del
   repositorio exige esa ruta y el README raiz sigue siendo la puerta de entrada del jurado.
4. `docs/rubrica-evaluacion.md` y `docs/stack-tecnico.md` son fuentes canonicas externas al
   paquete de entregables. Se enlazan, no se duplican.
5. `docs/arquitectura.md` y `docs/informe-final.md` son vistas del MVP, no copias de las fuentes
   del reto. `specs/06...` es la fuente normativa de los diagramas; el informe debe declarar su
   fuente de estado y evidencia.
6. `mvp/deliverables/` contiene manifiestos, vistas publicadas y artefactos finales. Cuando una
   vista sea una copia sincronizada de `specs/` o `docs/`, debe declarar procedencia, fecha y
   commit; solo una ubicacion puede ser autora.
7. El video puede ser un enlace externo o un archivo gestionado con Git LFS; no se decide por
   defecto en esta spec.

## Estructura objetivo

La estructura siguiente es objetivo de migracion, no un estado ya aplicado:

```text
mvp/
  README.md
  crisp-dm/
    README.md
    01_business_understanding/README.md
    02_data_understanding/README.md
    03_data_preparation/README.md
    04_modeling/README.md
    05_evaluation/README.md
    06_deployment/README.md
  deliverables/
    01_repository/README.md
    02_architecture/README.md
    02_architecture/architecture.md
    03_final_report/README.md
    03_final_report/final_report.md
    03_final_report/evidence/
    04_video/README.md
    04_video/demo_script.md
    04_video/evidence_index.md

app/                    Runtime FastAPI, servicios y web
scripts/                Validadores y bootstrap
tests/                  Pruebas automatizadas
specs/                  Fuente normativa de requisitos, plan y tareas
readme/                 Setup, demo, metricas y bitacora
.env.example            Plantilla de configuracion, en la raiz
dataset/                Fuente canonica local, fuera de mvp/
docs/                   Rubrica y stack canonicos, fuera de mvp/
data/                   Estado generado local, fuera de mvp/
```

### Ownership de cada zona

| Zona | Fuente de verdad | Puede contener | No puede contener |
|---|---|---|---|
| `mvp/crisp-dm/` | Fases de proceso | objetivos, entradas, salidas, estado y enlaces | copias de dataset, docs o `data/` |
| `mvp/deliverables/` | Manifiestos y artefactos finales | diagrama, informe, video y evidencia redaccionada | secretos, runtime duplicado o fuentes canonicas copiadas |
| `specs/` | Requisitos y decisiones previas al codigo | specs, plan, tareas y dependencias | resultados inventados o implementaciones |
| `readme/` | Procedimientos operativos | setup, demo, metricas y sesiones | una segunda fuente normativa sin enlace |
| `app/`, `scripts/`, `tests/` | Implementacion | codigo, scripts y pruebas | paquetes de entrega duplicados |
| `dataset/`, `docs/rubrica-evaluacion.md`, `docs/stack-tecnico.md` | Reto canonico | archivos originales | movimiento, renombre o copia bajo `mvp/` |
| `docs/arquitectura.md`, `docs/informe-final.md` | Vistas publicadas del MVP | baseline y enlaces de procedencia | segunda autoria sin sincronizacion |
| `data/` | Runtime local | SQLite, uploads y JSONL | commit o inclusion en entregables |

## Entregables formales

### `mvp/deliverables/01_repository/`

Debe ser un manifiesto del repositorio entregado: README de entrada, dependencias, comandos,
commit evaluado, estado G1-G5 y referencia a las rutas de runtime. No debe contener una copia
de `app/`, `tests/`, `dataset/` ni `docs/`.

### `mvp/deliverables/02_architecture/`

Debe publicar la vista que el jurado recibe. La fuente normativa de sus bloques y flujos sera
`specs/06_system_flow_diagram_specification.md`; `docs/arquitectura.md` seguira siendo la vista
publicada de implementacion hasta que la migracion se apruebe. El manifiesto debe indicar:

- version de la spec del diagrama;
- commit y fecha de la vista;
- modelo y proveedor declarados;
- elementos `IMPLEMENTED`, `PROPOSED`, `MANUAL_PENDING` y `OUT_OF_SCOPE`;
- divergencias entre diagrama, codigo y evidencia.

### `mvp/deliverables/03_final_report/`

Debe contener el informe final y su indice de evidencia. `docs/informe-final.md` conserva el
estado documentado del checkout actual mientras la migracion no este aprobada. Ninguna version
puede cambiar un estado de gate sin evidencia fechada.

### `mvp/deliverables/04_video/`

Debe contener guion, indice de escenas, procedencia del commit y enlace o archivo del video.
El manifiesto debe registrar si el artefacto es externo, su URL, fecha y checksum cuando exista.
No debe guardar claves, tokens ni datos clinicos innecesarios.

## Dependencias

```text
README + rubrica + stack canonicos
             |
             v
specs/00_mvp_specification.md
             |
       +-----+-----+
       v           v
specs/01_plan  specs/02_tasks
       |
       v
03 estructura --> 04 admin --> 05 timeout
                         \       /
                          v     v
                    06 diagrama
                          |
                          v
                vistas en docs/ y mvp/deliverables/
```

La secuencia refleja que el diagrama depende de la estructura, del ciclo de documentos y del
timeout. Si una de esas specs cambia, `06_system_flow_diagram_specification.md` debe revisarse
antes de actualizar codigo o una vista publicada.

## Migracion por etapas

| Etapa | Accion futura | Verificacion | Regla de no regresion |
|---|---|---|---|
| 0. Inventario | Clasificar archivos y enlaces | manifiesto de rutas y enlaces rotos | no cambiar archivos |
| 1. Indices | Crear indices bajo `mvp/` | revisar ownership y procedencia | no duplicar fuentes |
| 2. CRISP-DM | Mover las seis fases a `mvp/crisp-dm/` | enlaces relativos y navegacion | no mover `dataset/` ni `docs/` |
| 3. Entregables | Crear los cuatro paquetes formales | cada paquete tiene README y fuente | no copiar runtime completo |
| 4. Vistas | Sincronizar arquitectura, informe e indices | matriz de procedencia | una sola autoridad por afirmacion |
| 5. Compatibilidad | Actualizar enlaces y README raiz | comandos desde raiz | no cambiar contrato runtime |
| 6. Preflight | Repetir pruebas y bootstrap | baseline comparable | no declarar gate por intencion |
| 7. Cierre | Registrar commit y pendientes | bitacora y estado final | no guardar secretos |

No se debe iniciar la etapa 2 hasta que las preguntas abiertas de ownership esten resueltas.

## Comandos de verificacion previstos

Estos comandos se ejecutaran solo durante la implementacion de la migracion. No se ejecutaron
en esta sesion:

```text
python -c "from pathlib import Path; required = ['mvp/README.md', 'mvp/crisp-dm/README.md', 'mvp/crisp-dm/01_business_understanding/README.md', 'mvp/crisp-dm/02_data_understanding/README.md', 'mvp/crisp-dm/03_data_preparation/README.md', 'mvp/crisp-dm/04_modeling/README.md', 'mvp/crisp-dm/05_evaluation/README.md', 'mvp/crisp-dm/06_deployment/README.md', 'mvp/deliverables/01_repository/README.md', 'mvp/deliverables/02_architecture/README.md', 'mvp/deliverables/03_final_report/README.md', 'mvp/deliverables/04_video/README.md', 'specs/06_system_flow_diagram_specification.md']; missing = [p for p in required if not Path(p).is_file()]; assert not missing, missing"
python -m pytest -q --basetemp <temp>
ruff check .
python -m scripts.validate_dataset
python -m app.bootstrap --data-dir <temp>
```

La revision estructural debe incluir una comprobacion de que no existen `mvp/dataset/`,
`mvp/docs/`, `mvp/app-copy/` ni `mvp/runtime-data/`, y una comprobacion de enlaces Markdown.

## Estilo documental y de codigo

- Las rutas de archivos se escriben con backticks y se enlazan con rutas relativas.
- Los nombres nuevos de archivos usan ingles y `snake_case`, siguiendo `specs/`.
- Los estados se escriben exactamente como `Documentado`, `Especificado`, `Pendiente de
  evidencia manual` y `Verificado` cuando describan evidencia.
- Los artefactos derivados incluyen fuente, fecha, commit y metodo de generacion.
- El codigo existente conserva `snake_case`, tipos explicitos en limites y logica clinica fuera
  de la autoridad del LLM.

## Estrategia de pruebas

La migracion es documental y de rutas. La prueba no debe demostrar una nueva funcionalidad
clinica; debe demostrar que la reubicacion no cambia el runtime:

- estructura: ownership, ausencia de copias prohibidas y rutas esperadas;
- enlaces: todos los enlaces relativos desde `mvp/`, `specs/`, `readme/` y `docs/` resuelven;
- runtime: suite, Ruff, validador y bootstrap mantienen resultados comparables al baseline;
- evidencia: cada gate conserva fecha, commit, entorno, comando o URL y resultado;
- manual: no convertir una reorganizacion documental en aprobacion de G2, G4 o G5.

Baseline de referencia del checkout: 38 tests, filas `3991/40/40/160`, 104 documentos,
103 `available` y 1 `needs_ocr`. No es una nueva verificacion de esta spec.

## Limites

- **Siempre:** conservar `dataset/` y `docs/` en sus rutas canonicas, usar enlaces en vez de
  copias, preservar comandos desde la raiz y registrar procedencia.
- **Preguntar antes:** mover `app/`, `scripts/`, `tests/`, `specs/` o `readme/`; cambiar el
  esquema de persistencia; incorporar Git LFS; cambiar el modelo; modificar `dataset/` o los
  documentos canonicos de `docs/`.
- **Nunca:** copiar fuentes canonicas bajo `mvp/`, incluir `data/`, commitear secretos,
  presentar un manifiesto como evidencia de ejecucion o declarar un gate aprobado sin prueba.

## Criterios de exito

- **STR-AC-01:** los cuatro entregables formales tienen una ruta bajo `mvp/deliverables/`.
- **STR-AC-02:** las seis fases tienen una ruta bajo `mvp/crisp-dm/` y conservan sus enlaces.
- **STR-AC-03:** `dataset/` y `docs/` no se mueven, renombran, modifican ni duplican.
- **STR-AC-04:** `app/`, `scripts/`, `tests/`, `specs/`, `readme/` y `data/` tienen ownership
  documentado y no aparecen copiados dentro del paquete.
- **STR-AC-05:** el README raiz conserva el setup, las URLs y los comandos de preflight.
- **STR-AC-06:** el informe, el diagrama y la evidencia declaran procedencia y estado real.
- **STR-AC-07:** el baseline de runtime permanece comparable despues de la migracion.
- **STR-AC-08:** una modificacion posterior de admin o timeout obliga a revisar la spec del
  diagrama antes de aceptar cambios de codigo.

## Preguntas abiertas

1. Confirmar si `docs/arquitectura.md` sera una vista derivada permanente o si la publicacion
   final se trasladara a `mvp/deliverables/02_architecture/`.
2. Confirmar si `docs/informe-final.md` sera la autoria del informe o si la autoria final sera
   `mvp/deliverables/03_final_report/final_report.md`.
3. Confirmar si el video se guardara mediante Git LFS, release o URL externa con checksum.
4. Confirmar si la evidencia por fase vivira en `mvp/crisp-dm/` o en el paquete del informe.
5. Confirmar si `readme/` y `specs/` deben permanecer en la raiz de forma permanente.
6. Confirmar si el runtime seguira en la raiz o tendra una spec independiente para `mvp/runtime/`.
