(() => {
  "use strict";

  const STORAGE_KEY = "techsphere.demo.session.v1";
  const DEMO_SESSION_VERSION = 1;
  const DEMO_PASSWORD = "12345";
  const ROLES = new Set(["patient", "admin"]);

  function clean(value, maxLength = 200) {
    return String(value ?? "").trim().slice(0, maxLength);
  }

  function validDay(value) {
    if (value === "" || value === null || value === undefined) return null;
    const day = Number(value);
    return Number.isInteger(day) && day >= 0 && day <= 3650 ? day : null;
  }

  function patientContext(fields = {}, mode = "returning") {
    return {
      procedure: clean(fields.procedure || "seguimiento postoperatorio"),
      dayPostop: validDay(fields.dayPostop),
      mode,
    };
  }

  function createPatientSession(fields = {}) {
    const mode = fields.mode === "new" ? "new" : "returning";
    const name = clean(fields.name);
    const patientId = clean(fields.patientId);
    const procedure = clean(fields.procedure || "seguimiento postoperatorio");
    if (!name && !patientId) return { ok: false, code: "PATIENT_IDENTIFIER_REQUIRED" };
    if (mode === "new" && (!name || !procedure)) return { ok: false, code: "PATIENT_CONTEXT_REQUIRED" };
    if (fields.dayPostop !== "" && validDay(fields.dayPostop) === null) {
      return { ok: false, code: "PATIENT_DAY_INVALID" };
    }
    return {
      ok: true,
      session: {
        version: DEMO_SESSION_VERSION,
        role: "patient",
        subject: { name, patientId, adminId: null },
        patientContext: patientContext({ procedure, dayPostop: fields.dayPostop }, mode),
        accessMode: mode,
        demoOnly: true,
        createdAt: new Date().toISOString(),
      },
    };
  }

  function createAdminSession(adminId) {
    const identifier = clean(adminId);
    if (!identifier) return { ok: false, code: "ADMIN_IDENTIFIER_REQUIRED" };
    return {
      ok: true,
      session: {
        version: DEMO_SESSION_VERSION,
        role: "admin",
        subject: { name: "", patientId: "", adminId: identifier },
        patientContext: null,
        accessMode: "admin",
        demoOnly: true,
        createdAt: new Date().toISOString(),
      },
    };
  }

  function isValidSession(value) {
    if (!value || typeof value !== "object") return false;
    if (value.version !== DEMO_SESSION_VERSION || !ROLES.has(value.role) || value.demoOnly !== true) return false;
    if (!value.subject || typeof value.subject !== "object") return false;
    if (value.role === "admin") return Boolean(clean(value.subject.adminId));
    if (!value.patientContext || typeof value.patientContext !== "object") return false;
    return Boolean(clean(value.subject.name) || clean(value.subject.patientId));
  }

  function save(session) {
    if (!isValidSession(session)) return false;
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
      return true;
    } catch (_error) {
      return false;
    }
  }

  function clear() {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch (_error) {
      // Storage can be unavailable in a restricted browser context.
    }
  }

  function get() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const session = JSON.parse(raw);
      if (!isValidSession(session)) {
        clear();
        return null;
      }
      return session;
    } catch (_error) {
      clear();
      return null;
    }
  }

  window.DemoSession = Object.freeze({
    DEMO_PASSWORD,
    DEMO_SESSION_VERSION,
    STORAGE_KEY,
    clear,
    createAdminSession,
    createPatientSession,
    get,
    isValidSession,
    save,
  });
})();
