(() => {
  "use strict";

  const sessionApi = window.DemoSession;
  const page = document.body.dataset.page;
  const $ = (selector) => document.querySelector(selector);

  const copy = {
    PATIENT_IDENTIFIER_REQUIRED: "Escribe tu nombre o tu ID para continuar.",
    PATIENT_CONTEXT_REQUIRED: "Para una nueva sesión necesitamos tu nombre y procedimiento.",
    PATIENT_DAY_INVALID: "El día postoperatorio debe estar entre 0 y 3650.",
    ADMIN_IDENTIFIER_REQUIRED: "Escribe el ID o usuario del administrador.",
    PASSWORD_INVALID: "La clave demo no coincide. Inténtalo de nuevo.",
    STORAGE_UNAVAILABLE: "No pudimos conservar la sesión en esta pestaña. Revisa el navegador.",
  };

  function setStatus(text, kind = "") {
    const status = $("#access-status");
    if (!status) return;
    status.textContent = text;
    status.className = `form-status ${kind}`.trim();
  }

  function demoPasswordIsValid(value) {
    return value === sessionApi?.DEMO_PASSWORD;
  }

  function initPatientAccess() {
    const form = $("#patient-access-form");
    const mode = $("#patient-mode");
    const context = $("#new-patient-context");
    const toggleContext = () => {
      const isNew = mode?.value === "new";
      if (context) context.hidden = !isNew;
      $("#patient-name")?.toggleAttribute("required", isNew);
      $("#procedure")?.toggleAttribute("required", isNew);
    };
    mode?.addEventListener("change", toggleContext);
    toggleContext();
    form?.addEventListener("submit", (event) => {
      event.preventDefault();
      const password = $("#patient-password")?.value || "";
      if (!demoPasswordIsValid(password)) {
        setStatus(copy.PASSWORD_INVALID, "error");
        return;
      }
      const result = sessionApi.createPatientSession({
        mode: mode?.value,
        name: $("#patient-name")?.value,
        patientId: $("#patient-id")?.value,
        procedure: $("#procedure")?.value,
        dayPostop: $("#day-postop")?.value,
      });
      if (!result.ok) {
        setStatus(copy[result.code] || "Revisa los datos e inténtalo de nuevo.", "error");
        return;
      }
      if (!sessionApi.save(result.session)) {
        setStatus(copy.STORAGE_UNAVAILABLE, "error");
        return;
      }
      window.location.assign("/call");
    });
  }

  function initAdminAccess() {
    const form = $("#admin-access-form");
    form?.addEventListener("submit", (event) => {
      event.preventDefault();
      const password = $("#admin-password")?.value || "";
      if (!demoPasswordIsValid(password)) {
        setStatus(copy.PASSWORD_INVALID, "error");
        return;
      }
      const result = sessionApi.createAdminSession($("#admin-id")?.value);
      if (!result.ok) {
        setStatus(copy[result.code] || "Revisa los datos e inténtalo de nuevo.", "error");
        return;
      }
      if (!sessionApi.save(result.session)) {
        setStatus(copy.STORAGE_UNAVAILABLE, "error");
        return;
      }
      window.location.assign("/admin");
    });
  }

  if (sessionApi && page === "patient-access") initPatientAccess();
  if (sessionApi && page === "admin-access") initAdminAccess();
})();
