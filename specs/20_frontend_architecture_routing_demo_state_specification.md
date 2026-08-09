# Spec: Arquitectura frontend, routing y estado demo por roles

**ID:** `FRONTEND-ARCH-020`
**Estado:** `PROPOSED`; especificación previa a implementación
**Versión:** 0.1.0
**Fecha:** 2026-08-09
**Propietario:** superficie web, navegación y sesión demo
**Depende de:** [`00_mvp_specification.md`](00_mvp_specification.md), [`03_mvp_structure_specification.md`](03_mvp_structure_specification.md), [`06_system_flow_diagram_specification.md`](06_system_flow_diagram_specification.md), [`11_conversational_ux_writing_specification.md`](11_conversational_ux_writing_specification.md)
**Coordina con:** [`21_patient_portal_call_ux_specification.md`](21_patient_portal_call_ux_specification.md) y [`22_audio_engine_continuous_vad_specification.md`](22_audio_engine_continuous_vad_specification.md)

## Objective

Convertir la entrada actual directa a `/call` en un recorrido demo comprensible: una landing
que explique el producto, un acceso de paciente, un acceso de administrador y un contexto de
paciente que llegue a la llamada sin autenticación real. La demo debe diferenciar vistas por
estado local, no simular una garantía de identidad.

### Supuestos explícitos

1. La aplicación continúa siendo FastAPI con HTML, CSS y JavaScript sin bundler; no se agrega
   React, Zustand ni una dependencia de autenticación para resolver un problema que el fork no
   tiene.
2. La contraseña fija `12345` es una credencial pública de demostración. Nunca protege datos
   reales, no se registra en logs y no se presenta como autenticación.
3. `sessionStorage` es suficiente para conservar el contexto dentro de una pestaña demo. Se
   evita `localStorage` para que el contexto del paciente desaparezca al cerrar la pestaña.
4. El backend existente sigue creando la llamada mediante `POST /api/calls`; el estado de rol
   del navegador no autoriza operaciones nuevas sobre la API.
5. `/admin` mantiene la consola de conocimiento existente, pero su entrada visible pasa por el
   acceso demo de administrador.

### Historias de usuario

- Como visitante, quiero entender qué hace la plataforma y elegir Paciente o Admin.
- Como paciente nuevo, quiero completar nombre, identificación opcional, procedimiento y día
  postoperatorio antes de iniciar la llamada.
- Como paciente recurrente de la demo, quiero escribir mi nombre o ID y continuar con la clave
  `12345` para recuperar mi contexto local.
- Como administrador, quiero escribir un usuario/ID y `12345` para llegar a `/admin`.
- Como evaluador, quiero recargar `/call` sin perder el contexto durante la pestaña y distinguir
  claramente que todo es una demo sin autenticación real.

## Tech Stack

- Python 3.11+, FastAPI y Uvicorn: entrega de páginas y API existentes.
- HTML semántico, CSS existente y JavaScript ES2022 en módulos pequeños bajo `app/web/`.
- `sessionStorage` con un esquema versionado `techsphere.demo.session.v1`.
- API existente: `POST /api/calls`, `GET /api/calls/{call_id}`, `POST /api/calls/{call_id}/finish`.
- Sin JWT, cookies de sesión, proveedor OAuth, backend de usuarios o base de credenciales.
- Modelo de razonamiento sin cambios: familia Meta Llama mediante el proveedor ya declarado; la
  sesión demo no altera el modelo permitido por `docs/stack-tecnico.md`.

## Commands

Los comandos deben ejecutarse desde la raíz y mantenerse sincronizados con `README.md`:

```text
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.bootstrap
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m pytest tests/test_http_contracts.py tests/test_calls.py -q
python -m pytest tests/test_demo_access.py tests/test_frontend_routes.py -q
node --check app/web/app.js
git diff --check
```

`tests/test_demo_access.py` y `tests/test_frontend_routes.py` son archivos objetivo de esta
spec; mientras no existan, el criterio no se puede declarar cumplido.

## Project Structure

```text
app/main.py                         -> GET /, /patient, /admin, /call y API existente
app/web/index.html                  -> landing y selección de entrada
app/web/patient-access.html         -> registro/contexto y acceso recurrente
app/web/admin-access.html           -> acceso demo de administrador
app/web/call.html                   -> portal de llamada, sin formulario de alta
app/web/session.js                  -> contrato y transiciones de sesión demo
app/web/access.js                   -> validación de formularios y navegación
app/web/app.js                      -> llamada, turnos, trazabilidad y audio
app/web/styles.css                  -> tokens y layout compartidos
tests/test_demo_access.py           -> contrato de estado, clave y aislamiento de roles
tests/test_frontend_routes.py       -> páginas, enlaces, formularios y ausencia del alta en /call
specs/20_*.md                       -> fuente normativa de esta arquitectura
```

### Routing

| Ruta | Superficie | Entrada | Resultado | Protección real |
|---|---|---|---|---|
| `/` | Landing | visitante | elige Paciente o Admin | ninguna |
| `/patient` | Acceso paciente | nombre/ID, clave y, si es nuevo, contexto clínico mínimo | `/call` con sesión demo válida | ninguna |
| `/admin` | Consola admin | usuario/ID y clave | inventario de documentos | ninguna; solo diferenciación visual demo |
| `/call` | Portal paciente | sesión demo en `sessionStorage` | llamada browser/API | ninguna |
| `/health` | health técnico | sistema/evaluador | estado de servicios, sin sesión | ninguna |

En la primera implementación, FastAPI debe servir páginas dedicadas. Si el equipo prefiere una
sola shell con History API, debe conservar las mismas URLs observables y añadir una prueba de
recarga directa para evitar rutas que funcionan solo después de navegar desde `/`.

### Contrato de sesión demo

```js
const DEMO_SESSION_VERSION = 1;

const session = {
  version: DEMO_SESSION_VERSION,
  role: "patient", // "patient" | "admin"
  subject: { name: "Ana María", patientId: "pac-001", adminId: null },
  patientContext: {
    procedure: "apendicectomía",
    dayPostop: 3,
  },
  accessMode: "new" , // "new" | "returning" | "admin"
  demoOnly: true,
  createdAt: "2026-08-09T00:00:00.000Z",
};
```

Reglas del contrato:

- `role` es obligatorio y solo admite `patient` o `admin`.
- Paciente nuevo requiere nombre y procedimiento; `patientId` y `dayPostop` son opcionales con
  las mismas longitudes y rangos de `StartCallRequest`.
- Paciente recurrente debe aportar nombre o ID; nunca se exige que existan en un registro real.
- Admin requiere `adminId` no vacío; no recibe contexto clínico.
- La clave se compara en memoria contra `12345`, nunca se guarda en el objeto ni se envía a la
  API.
- El objeto se elimina al cerrar sesión demo, al cambiar de rol y ante una versión desconocida.
- `/call` no inicia una llamada si no existe una sesión `patient` válida; redirige a `/patient`.
- El código debe tratar el contenido de `sessionStorage` como entrada no confiable y escapar todo
  valor al insertarlo en DOM.

### Transiciones

```text
VISITOR -> LANDING
LANDING --Paciente--> PATIENT_ACCESS
LANDING --Admin-----> ADMIN_ACCESS
PATIENT_ACCESS --nuevo + 12345--> PATIENT_SESSION -> /call
PATIENT_ACCESS --nombre o ID + 12345--> PATIENT_SESSION -> /call
ADMIN_ACCESS --admin ID + 12345--> ADMIN_SESSION -> /admin
SESSION --cerrar / limpiar--> LANDING
SESSION --JSON inválido o rol incorrecto--> ACCESS correspondiente
```

El formulario actual de `/call` se retira del portal. La llamada recibe el contexto desde la
sesión y lo usa para crear `POST /api/calls`; si el endpoint rechaza el contexto, se muestra un
error recuperable y no se inventa una llamada local.

## Code Style

Usar nombres en `camelCase` en JavaScript, funciones pequeñas, validación en el borde y una sola
fuente para mensajes visibles. No interpolar datos del paciente con `innerHTML`.

```js
export function validatePatientAccess(fields) {
  const name = fields.name.trim();
  const patientId = fields.patientId.trim();
  const password = fields.password;

  if (!name && !patientId) return { ok: false, code: "PATIENT_IDENTIFIER_REQUIRED" };
  if (password !== DEMO_PASSWORD) return { ok: false, code: "DEMO_PASSWORD_INVALID" };

  return {
    ok: true,
    session: createPatientSession({ name, patientId, context: fields.context }),
  };
}
```

Los identificadores visibles usan lenguaje de usuario (`Nombre`, `ID`, `Entrar como paciente`),
no `subject`, `JWT`, `claims` ni `role guard`. El aviso fijo de demo debe aparecer antes de la
clave y en el cierre: “Acceso de demostración: no uses datos reales”.

## Testing Strategy

### Unitarias

- validar que `12345` acepta y cualquier otra clave rechaza sin persistir la clave;
- aceptar nombre o ID para paciente recurrente, pero no un formulario vacío;
- validar contexto nuevo, `dayPostop` entre 0 y 3650 y longitudes máximas;
- rechazar JSON inválido, versión desconocida, rol extraño y datos de admin en `/call`;
- comprobar que `clearDemoSession()` elimina el contexto.

### Contratos de frontend/API

- las rutas HTML responden 200 y enlazan entre `/`, `/patient`, `/admin` y `/call`;
- el HTML de `/call` no contiene los campos de alta `patient-name`, `procedure` ni `day-postop`;
- `POST /api/calls` recibe solo el contexto clínico permitido, nunca `password`;
- una sesión admin no crea llamadas ni puede cambiar el inventario mediante el estado local;
- una recarga conserva la sesión de la misma pestaña y una nueva pestaña no hereda el contexto.

### Smoke manual

1. Abrir `/`, comprobar la tesis y ambos puntos de entrada.
2. Recorrer paciente nuevo, verificar el contexto en `/call` e iniciar la llamada.
3. Volver a cargar `/call`, comprobar que el contexto sigue visible.
4. Cerrar sesión y comprobar que `/call` devuelve a `/patient`.
5. Recorrer admin y comprobar que la consola conserva upload, estado y delete.
6. Intentar una clave distinta y confirmar un mensaje recuperable sin navegación.

## Boundaries

- **Always:** mantener el disclaimer demo, validar y normalizar en el cliente, no guardar la
  clave, usar `sessionStorage`, conservar el contrato API, escapar el contexto y ofrecer fallback
  textual en `/call`.
- **Ask first:** cambiar la credencial, persistir datos entre pestañas, agregar autenticación
  real, crear usuarios persistentes, cambiar el modelo permitido o exponer una nueva API.
- **Never:** presentar este flujo como autenticación, enviar la clave al backend, leer `dataset/`
  desde el navegador, colocar secretos en `.env.example`, bloquear `/admin` como si hubiera
  autorización real o aceptar datos clínicos que no llegan desde el contexto válido.

## Success Criteria

| ID | Criterio verificable | Evidencia |
|---|---|---|
| `ARCH-AC-01` | `/` explica la plataforma y ofrece Paciente/Admin | prueba de rutas + smoke |
| `ARCH-AC-02` | `/call` ya no contiene el formulario de alta | contrato HTML |
| `ARCH-AC-03` | paciente nuevo llega a `/call` con nombre, procedimiento e ID/día opcionales | integración API |
| `ARCH-AC-04` | paciente recurrente puede entrar con nombre o ID y `12345` | unitarias + smoke |
| `ARCH-AC-05` | admin entra con ID y `12345` a la consola sin contexto clínico | unitarias + smoke |
| `ARCH-AC-06` | la clave no aparece en `sessionStorage`, requests, eventos ni HTML generado | inspección automatizada |
| `ARCH-AC-07` | una sesión inválida no inicia llamada y ofrece recuperación | contrato frontend |
| `ARCH-AC-08` | el flujo permanece explícitamente fuera de G2 de credenciales reales | README, disclaimer y reporte |
| `ARCH-AC-09` | el arranque documentado sigue dentro de 15 minutos y no agrega descarga | README + preflight |

## Implementation Plan and Tasks

1. Servir landing y accesos en rutas directas, manteniendo `/admin` y `/call` existentes.
2. Extraer el formulario de `call.html` y crear el contrato `session.js`.
3. Crear validadores y estados de éxito/error para paciente y admin.
4. Conectar el contexto paciente a `POST /api/calls` y al encabezado del portal.
5. Añadir pruebas de rutas, aislamiento, no persistencia de clave y regresiones de llamadas.
6. Ejecutar el smoke manual y actualizar `README.md`, `docs/arquitectura.md` y la bitácora con
   evidencia real.

## Open Questions

1. ¿La demo debe mostrar `/admin` directo con un modal de acceso o usar una ruta separada
   `/admin/access` antes de llegar a la consola? Esta spec recomienda `/admin` como acceso visible
   solo si la implementación puede preservar enlaces existentes sin ambigüedad.
2. ¿Debe el botón de cierre limpiar solo la sesión demo o también cerrar la llamada activa? La
   opción segura es cerrar la llamada primero y luego limpiar.
3. La sesión demo no satisface autenticación real; el informe final debe declarar esta limitación
   y no usarla como evidencia de seguridad de producción.
