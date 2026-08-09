(() => {
  "use strict";

  const catalog = window.ARCHITECTURE_CATALOG;
  if (!catalog || !Array.isArray(catalog.entities)) return;

  const entities = catalog.entities;
  const entityMap = new Map(entities.map((item) => [item.entity_id, item]));
  const stageMap = new Map(catalog.stages.map((item) => [item.id, item]));
  const viewMap = new Map(catalog.views.map((item) => [item.id, item]));
  const statuses = ["IMPLEMENTED", "TESTED", "MANUAL_PENDING", "PROPOSED", "OUT_OF_SCOPE"];
  const kinds = [...new Set(entities.map((item) => item.kind))].sort();
  const surfaces = [...new Set(entities.map((item) => item.surface).filter(Boolean))].sort();
  const ownerships = [...new Set(entities.map((item) => item.ownership).filter(Boolean))].sort();
  const gates = [...new Set(entities.map((item) => item.gate).filter(Boolean))].sort();
  const views = catalog.views.map((item) => item.id);
  const stages = catalog.stages.map((item) => item.id);
  const state = {
    q: "",
    kind: "",
    status: "",
    view: "",
    stage: "",
    surface: "",
    ownership: "",
    gate: "",
    tested: false,
    manual: false,
    proposal: false,
    entity: "",
    opener: null,
  };

  const $ = (selector) => document.querySelector(selector);
  const normalize = (value) => String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const values = (value) => Array.isArray(value) ? value : (value ? [value] : []);
  const escapeRegExp = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  function queryTerms() {
    return normalize(state.q).split(" ").filter(Boolean);
  }

  function searchable(entity) {
    return [
      entity.entity_id, entity.kind, entity.title, entity.summary, entity.description,
      entity.status, entity.status_scope, entity.surface, entity.ownership, entity.gate,
      ...values(entity.views), ...values(entity.stages), ...values(entity.tags),
      ...values(entity.code_refs), ...values(entity.test_refs), ...values(entity.inputs),
      ...values(entity.outputs), ...values(entity.source_refs).map((item) => typeof item === "object" ? item.label : item),
    ].map(normalize).join(" ");
  }

  function matchesQuery(entity, terms) {
    if (!terms.length) return true;
    const haystack = searchable(entity);
    return terms.every((term) => haystack.includes(term));
  }

  function matchesFilters(entity) {
    if (state.kind && entity.kind !== state.kind) return false;
    if (state.status && entity.status !== state.status) return false;
    if (state.view && !values(entity.views).includes(state.view)) return false;
    if (state.stage && !values(entity.stages).includes(state.stage)) return false;
    if (state.surface && entity.surface !== state.surface) return false;
    if (state.ownership && entity.ownership !== state.ownership) return false;
    if (state.gate && entity.gate !== state.gate) return false;
    if (state.tested && !entity.automated_test) return false;
    if (state.manual && !entity.manual_pending) return false;
    if (state.proposal && !["PROPOSED", "OUT_OF_SCOPE"].includes(entity.status)) return false;
    return matchesQuery(entity, queryTerms());
  }

  function filteredEntities() {
    return entities.filter(matchesFilters);
  }

  function setText(node, value) {
    if (node) node.textContent = value === undefined || value === null ? "" : String(value);
    return node;
  }

  function appendHighlighted(node, value) {
    const text = String(value || "");
    const terms = queryTerms().filter((term) => term.length > 1);
    if (!node || !terms.length) return setText(node, text);
    const expression = new RegExp(`(${terms.map(escapeRegExp).join("|")})`, "ig");
    let cursor = 0;
    let match;
    while ((match = expression.exec(text)) !== null) {
      node.appendChild(document.createTextNode(text.slice(cursor, match.index)));
      const mark = document.createElement("mark");
      mark.textContent = match[0];
      node.appendChild(mark);
      cursor = match.index + match[0].length;
    }
    node.appendChild(document.createTextNode(text.slice(cursor)));
    return node;
  }

  function readHash() {
    const params = new URLSearchParams(location.hash.startsWith("#") ? location.hash.slice(1) : "");
    const valid = (value, allowed) => allowed.includes(value) ? value : "";
    state.q = params.get("q")?.slice(0, 120) || "";
    state.kind = valid(params.get("kind") || "", kinds);
    state.status = valid(params.get("status") || "", statuses);
    state.view = valid(params.get("view") || "", views);
    state.stage = valid(params.get("stage") || "", stages);
    state.surface = valid(params.get("surface") || "", surfaces);
    state.ownership = valid(params.get("ownership") || "", ownerships);
    state.gate = valid(params.get("gate") || "", gates);
    state.tested = params.get("tested") === "1";
    state.manual = params.get("manual") === "1";
    state.proposal = params.get("proposal") === "1";
    state.entity = entityMap.has(params.get("entity")) ? params.get("entity") : "";
  }

  function writeHash() {
    const params = new URLSearchParams();
    const fields = [
      ["q", state.q], ["kind", state.kind], ["status", state.status], ["view", state.view],
      ["stage", state.stage], ["surface", state.surface], ["ownership", state.ownership], ["gate", state.gate],
    ];
    fields.forEach(([key, value]) => { if (value) params.set(key, value); });
    if (state.tested) params.set("tested", "1");
    if (state.manual) params.set("manual", "1");
    if (state.proposal) params.set("proposal", "1");
    if (state.entity) params.set("entity", state.entity);
    const next = params.toString();
    if (location.hash.slice(1) !== next) location.hash = next;
  }

  function option(label, value, count, selected) {
    const item = document.createElement("option");
    item.value = value;
    item.textContent = count === undefined ? label : `${label} (${count})`;
    item.selected = selected;
    return item;
  }

  function countFor(field, value) {
    return entities.filter((item) => {
      if (field === "kind") return item.kind === value;
      if (field === "status") return item.status === value;
      if (field === "view") return values(item.views).includes(value);
      if (field === "stage") return values(item.stages).includes(value);
      if (field === "surface") return item.surface === value;
      if (field === "ownership") return item.ownership === value;
      if (field === "gate") return item.gate === value;
      return false;
    }).length;
  }

  function fillSelect(id, valuesList, selected, labels, field) {
    const select = $(`#${id}`);
    if (!select) return;
    select.replaceChildren(option("Todos", "", undefined, !selected));
    valuesList.forEach((value) => select.appendChild(option(labels?.[value] || value, value, countFor(field, value), value === selected)));
  }

  function syncControls() {
    setText($("#catalog-search"), state.q);
    $("#catalog-search").value = state.q;
    fillSelect("kind-filter", kinds, state.kind, { ACT: "Actor", UI: "Interfaz", API: "API", STG: "Etapa", MOD: "Modulo", EXT: "Externo", DATA: "Dato", STATE: "Estado", RULE: "Regla", MET: "Metrica", TRZ: "Trazabilidad", TEST: "Prueba", GATE: "Gate" }, "kind");
    fillSelect("status-filter", statuses, state.status, {}, "status");
    fillSelect("view-filter", views, state.view, {}, "view");
    fillSelect("stage-filter", stages, state.stage, {}, "stage");
    fillSelect("surface-filter", surfaces, state.surface, {}, "surface");
    fillSelect("ownership-filter", ownerships, state.ownership, {}, "ownership");
    fillSelect("gate-filter", gates, state.gate, {}, "gate");
    $("#tested-filter").checked = state.tested;
    $("#manual-filter").checked = state.manual;
    $("#proposal-filter").checked = state.proposal;
  }

  function statusClass(status) {
    return { IMPLEMENTED: "implemented", TESTED: "tested", MANUAL_PENDING: "pending", PROPOSED: "proposed", OUT_OF_SCOPE: "out" }[status] || "pending";
  }

  function createStageList() {
    const list = $("#stage-list");
    if (!list) return;
    list.replaceChildren();
    catalog.stages.forEach((stage) => {
      const item = document.createElement("li");
      item.className = "stage-item";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "stage-button";
      button.setAttribute("aria-pressed", String(state.stage === stage.id));
      const id = document.createElement("span");
      id.className = "stage-id";
      setText(id, stage.id);
      const title = document.createElement("span");
      title.className = "stage-title";
      setText(title, stage.title);
      const summary = document.createElement("p");
      summary.className = "stage-summary";
      setText(summary, stage.summary);
      button.append(id, title, summary);
      button.addEventListener("click", () => {
        state.stage = state.stage === stage.id ? "" : stage.id;
        state.entity = "";
        writeHash();
        render();
      });
      item.appendChild(button);
      list.appendChild(item);
    });
  }

  function createViews() {
    const list = $("#view-list");
    if (!list) return;
    list.replaceChildren();
    catalog.views.forEach((view) => {
      const card = document.createElement("article");
      card.className = `view-card${state.view === view.id ? " is-active" : ""}`;
      const heading = document.createElement("div");
      heading.className = "view-card-header";
      const id = document.createElement("span");
      id.className = "view-id";
      setText(id, view.id);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "view-filter-button";
      button.setAttribute("aria-current", state.view === view.id ? "true" : "false");
      setText(button, state.view === view.id ? "Quitar filtro" : "Filtrar catalogo");
      button.addEventListener("click", () => {
        state.view = state.view === view.id ? "" : view.id;
        state.entity = "";
        writeHash();
        render();
      });
      heading.append(id, button);
      const title = document.createElement("h3");
      setText(title, view.title);
      const question = document.createElement("p");
      question.className = "view-question";
      setText(question, view.question);
      const map = document.createElement("ul");
      map.className = "view-map";
      view.entity_ids.forEach((idValue) => {
        const entry = document.createElement("li");
        setText(entry, idValue);
        map.appendChild(entry);
      });
      card.append(heading, title, question, map);
      list.appendChild(card);
    });
  }

  function addDetailSection(parent, title, value, asLinks = false) {
    const section = document.createElement("section");
    section.className = "detail-section";
    const heading = document.createElement("h3");
    setText(heading, title);
    section.appendChild(heading);
    const listValues = values(value);
    if (asLinks) {
      const list = document.createElement("ul");
      list.className = "detail-links";
      listValues.forEach((item) => {
        const row = document.createElement("li");
        if (typeof item === "object" && item.href && /^\.\.?\//.test(item.href) && !item.href.includes(":")) {
          const link = document.createElement("a");
          link.href = item.href;
          setText(link, item.label || item.href);
          row.appendChild(link);
        } else {
          setText(row, typeof item === "object" ? item.label : item);
        }
        list.appendChild(row);
      });
      section.appendChild(list);
    } else if (listValues.length) {
      const list = document.createElement("ul");
      listValues.forEach((item) => {
        const row = document.createElement("li");
        setText(row, item);
        list.appendChild(row);
      });
      section.appendChild(list);
    } else {
      const empty = document.createElement("p");
      setText(empty, "No registrado en esta vista documental.");
      section.appendChild(empty);
    }
    parent.appendChild(section);
  }

  function openDetail(id, opener = null) {
    const entity = entityMap.get(id);
    if (!entity) return;
    state.entity = id;
    state.opener = opener;
    writeHash();
    const dialog = $("#entity-detail");
    setText($("#detail-kind"), `${entity.kind} · ${entity.ownership}`);
    setText($("#detail-title"), entity.title);
    setText($("#detail-id"), entity.entity_id);
    setText($("#detail-summary"), entity.summary);
    const content = $("#detail-content");
    content.replaceChildren();
    addDetailSection(content, "Estado y alcance", [`${entity.status}: ${entity.status_scope}`, entity.evidence]);
    addDetailSection(content, "Entradas", entity.inputs);
    addDetailSection(content, "Salidas", entity.outputs);
    addDetailSection(content, "Invariantes y seguridad", entity.invariants);
    addDetailSection(content, "Código y contratos", entity.code_refs);
    addDetailSection(content, "Pruebas y comandos", entity.test_refs);
    addDetailSection(content, "Vistas, etapas y tags", [...values(entity.views), ...values(entity.stages), ...values(entity.tags)]);
    addDetailSection(content, "Fuentes", entity.source_refs, true);
    const related = document.createElement("section");
    related.className = "detail-section";
    const relatedHeading = document.createElement("h3");
    setText(relatedHeading, "Entidades relacionadas");
    related.appendChild(relatedHeading);
    const relatedList = document.createElement("div");
    relatedList.className = "detail-chips";
    values(entity.related_ids).forEach((relatedId) => {
      const relatedButton = document.createElement("button");
      relatedButton.type = "button";
      relatedButton.className = "detail-chip";
      setText(relatedButton, relatedId);
      relatedButton.disabled = !entityMap.has(relatedId);
      relatedButton.addEventListener("click", () => openDetail(relatedId, relatedButton));
      relatedList.appendChild(relatedButton);
    });
    related.appendChild(relatedList);
    content.appendChild(related);
    addDetailSection(content, "Divergencias", entity.divergences);
    if (typeof dialog.showModal === "function" && !dialog.open) dialog.showModal();
    else dialog.hidden = false;
    if (opener) opener.setAttribute("aria-expanded", "true");
    $("#detail-close")?.focus();
  }

  function closeDetail() {
    const dialog = $("#entity-detail");
    if (dialog?.open && typeof dialog.close === "function") dialog.close();
    else if (dialog) dialog.hidden = true;
    state.entity = "";
    if (state.opener) state.opener.setAttribute("aria-expanded", "false");
    state.opener?.focus?.();
    state.opener = null;
    writeHash();
  }

  function createEntityCard(entity) {
    const card = document.createElement("article");
    card.className = `entity-card ownership-${normalize(entity.ownership).replace(/ /g, "-")}`;
    const header = document.createElement("div");
    header.className = "entity-header";
    const heading = document.createElement("div");
    const kind = document.createElement("span");
    kind.className = "entity-kind";
    setText(kind, `${entity.kind} · ${entity.surface}`);
    const id = document.createElement("p");
    id.className = "entity-id";
    appendHighlighted(id, entity.entity_id);
    heading.append(kind, id);
    const status = document.createElement("span");
    status.className = `status ${statusClass(entity.status)}`;
    setText(status, entity.status);
    header.append(heading, status);
    const title = document.createElement("h3");
    title.className = "entity-title";
    appendHighlighted(title, entity.title);
    const summary = document.createElement("p");
    summary.className = "entity-summary";
    appendHighlighted(summary, entity.summary);
    const footer = document.createElement("div");
    footer.className = "entity-footer";
    const ownership = document.createElement("span");
    ownership.className = "ownership-label";
    setText(ownership, `Ownership: ${entity.ownership}`);
    const open = document.createElement("button");
    open.type = "button";
    open.className = "entity-open";
    open.setAttribute("aria-controls", "entity-detail");
    open.setAttribute("aria-expanded", state.entity === entity.entity_id ? "true" : "false");
    setText(open, "Abrir detalle");
    open.addEventListener("click", () => openDetail(entity.entity_id, open));
    footer.append(ownership, open);
    card.append(header, title, summary, footer);
    return card;
  }

  function renderResults() {
    const results = $("#catalog-results");
    if (!results) return;
    const matching = filteredEntities();
    results.replaceChildren();
    setText($("#filter-summary"), `${matching.length} de ${entities.length} entidades · ${activeFilterText()}`);
    if (!matching.length) {
      const empty = document.createElement("p");
      empty.className = "empty-results";
      setText(empty, "No encontramos entidades con esta combinación. Cambia la búsqueda o limpia alguno de los filtros.");
      results.appendChild(empty);
      return;
    }
    matching.forEach((entity) => results.appendChild(createEntityCard(entity)));
  }

  function activeFilterText() {
    const active = [];
    if (state.q) active.push(`búsqueda “${state.q}”`);
    if (state.status) active.push(state.status);
    if (state.kind) active.push(state.kind);
    if (state.view) active.push(state.view);
    if (state.stage) active.push(state.stage);
    if (state.surface) active.push(state.surface);
    if (state.ownership) active.push(state.ownership);
    if (state.gate) active.push(state.gate);
    if (state.tested) active.push("con prueba");
    if (state.manual) active.push("manual pendiente");
    if (state.proposal) active.push("propuesta/fuera de alcance");
    return active.length ? `Filtros: ${active.join(", ")}` : "sin filtros";
  }

  function renderGlossary() {
    const list = $("#glossary-list");
    if (!list) return;
    list.replaceChildren();
    catalog.glossary.forEach(([term, definition]) => {
      const wrapper = document.createElement("div");
      const name = document.createElement("dt");
      setText(name, term);
      const detail = document.createElement("dd");
      setText(detail, definition);
      wrapper.append(name, detail);
      list.appendChild(wrapper);
    });
  }

  function render() {
    syncControls();
    createStageList();
    createViews();
    renderResults();
    renderGlossary();
    if (state.entity && !$("#entity-detail")?.open) openDetail(state.entity);
  }

  function updateField(name, value) {
    state[name] = value;
    state.entity = "";
    writeHash();
    render();
  }

  function init() {
    setText($("#generated-at"), catalog.meta.generated_at);
    setText($("#catalog-commit"), catalog.meta.commit);
    setText($("#footer-date"), catalog.meta.generated_at);
    readHash();
    const selectFields = ["kind", "status", "view", "stage", "surface", "ownership", "gate"];
    selectFields.forEach((name) => $(`#${name}-filter`)?.addEventListener("change", (event) => updateField(name, event.target.value)));
    $("#catalog-search")?.addEventListener("input", (event) => {
      state.q = event.target.value.slice(0, 120);
      state.entity = "";
      writeHash();
      render();
    });
    [["tested-filter", "tested"], ["manual-filter", "manual"], ["proposal-filter", "proposal"]].forEach(([id, name]) => {
      $(`#${id}`)?.addEventListener("change", (event) => updateField(name, event.target.checked));
    });
    $("#clear-filters")?.addEventListener("click", () => {
      Object.assign(state, { q: "", kind: "", status: "", view: "", stage: "", surface: "", ownership: "", gate: "", tested: false, manual: false, proposal: false, entity: "" });
      writeHash();
      render();
    });
    $("#detail-close")?.addEventListener("click", closeDetail);
    $("#entity-detail")?.addEventListener("cancel", (event) => { event.preventDefault(); closeDetail(); });
    window.addEventListener("hashchange", () => { readHash(); render(); });
    render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
