/*
 * Editor entry point: wires the store, canvas, properties panel, toolbox,
 * keyboard shortcuts, autosave and export together.
 */
import { Store } from "./state.js";
import { Canvas } from "./canvas.js";
import { Panel } from "./panel.js";
import { Saver, exportDiagram } from "./io.js";
import { clearTextCache } from "./geometry.js";

const $ = (sel) => document.querySelector(sel);
const data = JSON.parse($("#diagram-data").textContent);
const config = JSON.parse($("#editor-config").textContent);
const rules = config.rules;
const canEdit = config.canEdit;
const notify = (message, type = "success") => window.UI.toast(message, type);

const store = new Store(data);

// =====================================================================
// factory: default elements & relationship validation (rules from the server)
// =====================================================================
const DEFAULT_NAMES = {
  class: "Class", interface: "Interface", enumeration: "Enumeration",
  actor: "Actor", usecase: "Use case", system: "System",
};

function uniqueName(base, kind) {
  const classifier = rules.kindsWithAttributes.includes(kind);
  const taken = new Set(store.doc.elements
    .filter((e) => (classifier ? rules.kindsWithAttributes.includes(e.kind) : e.kind === kind))
    .map((e) => e.name.toLowerCase()));
  const sep = classifier ? "" : " ";
  for (let i = 1; ; i++) {
    const name = `${base}${sep}${i}`;
    if (!taken.has(name.toLowerCase())) return name;
  }
}

const factory = {
  element(kind) {
    return {
      id: store.newId("e"),
      kind,
      name: uniqueName(DEFAULT_NAMES[kind] || "Element", kind),
      description: "",
      x: 0, y: 0, width: kind === "system" ? 420 : 160, height: kind === "system" ? 320 : 80,
      attributes: [],
      methods: [],
    };
  },

  relationship(type, source, target) {
    return { id: store.newId("r"), source, target, rel_type: type, label: "", source_cardinality: "", target_cardinality: "" };
  },

  /** Same rules as diagrams/rules.py relationship_error() + duplicates. */
  relationshipError(type, source, target, ignoreId = null) {
    if (!source || !target) return "Both ends must be selected.";
    if (source.id === target.id) return "An element cannot be connected to itself.";
    const diagramType = store.meta.diagramType;
    if (!rules.relationshipTypes[diagramType].includes(type)) return "This relationship is not allowed in this diagram.";
    if (rules.nonConnectableKinds.includes(source.kind) || rules.nonConnectableKinds.includes(target.kind)) {
      return "A system boundary cannot be connected.";
    }
    const pairs = rules.relationshipEndpoints[diagramType][type];
    const label = rules.relationshipLabels[type];
    if (pairs && !pairs.some(([s, t]) => s === source.kind && t === target.kind)) {
      const kl = rules.elementKindLabels;
      return `${label} cannot go from ${kl[source.kind].toLowerCase()} to ${kl[target.kind].toLowerCase()}.`;
    }
    const duplicate = store.doc.relationships.some((r) => r.id !== ignoreId && r.rel_type === type &&
      r.source === source.id && r.target === target.id);
    if (duplicate) return `This ${label.toLowerCase()} already exists.`;
    return null;
  },
};

// =====================================================================
// components
// =====================================================================
const editorEl = $("#editor");
const wrap = $("#canvas-wrap");
const titleInput = $("#diagram-title");
const hint = $("#canvas-hint");

const canvas = new Canvas({
  svgEl: $("#canvas"), wrap, store, rules, canEdit, factory, notify,
  onToolChange: (tool) => updateToolUi(tool),
});

const panel = new Panel({
  root: $("#properties"), store, rules, canEdit, factory, notify,
  onMetaChange: (field, value) => { if (field === "title" && document.activeElement !== titleInput) titleInput.value = value; },
});

const saver = new Saver({ store, url: config.apiUrl, statusEl: $("#save-status"), notify, enabled: canEdit });

// =====================================================================
// store -> UI
// =====================================================================
function refreshHistoryButtons() {
  const undo = $("#btn-undo"), redo = $("#btn-redo");
  if (undo) undo.disabled = !store.canUndo;
  if (redo) redo.disabled = !store.canRedo;
}

function refreshEmptyState() {
  $("#canvas-empty").hidden = store.doc.elements.length > 0;
}

store.on((type) => {
  if (type === "change" || type === "live" || type === "select") canvas.render();
  if (type === "change" || type === "select") panel.render();
  if (type === "change") { refreshHistoryButtons(); refreshEmptyState(); }
  if ((type === "change" || type === "meta") && store.dirty) saver.schedule();
  if (type === "meta") document.title = `${store.meta.title} · Smart UML`;
});

canvas.onViewChange((view) => { $("#btn-zoom-reset").textContent = `${Math.round(view.k * 100)}%`; });

// =====================================================================
// toolbox
// =====================================================================
const TOOL_HINTS = {
  add: (kind) => `Click on the canvas to place ${article(rules.elementKindLabels[kind])} — <kbd>Esc</kbd> to cancel`,
  connect: (type) => canvas.connectSource
    ? `Now click the <strong>target</strong> element — <kbd>Esc</kbd> to cancel`
    : `${rules.relationshipLabels[type]}: click the <strong>source</strong> element`,
};

function article(label) { return (/^[aeiou]/i.test(label) ? "an " : "a ") + label.toLowerCase(); }

function updateToolUi(tool) {
  document.querySelectorAll("#toolbox .tool").forEach((b) => b.classList.toggle("active", b.dataset.tool === tool));
  const [mode, arg] = tool.split(":");
  if (TOOL_HINTS[mode]) { hint.innerHTML = TOOL_HINTS[mode](arg); hint.hidden = false; }
  else hint.hidden = true;
}

document.querySelectorAll("#toolbox .tool").forEach((button) => {
  button.addEventListener("click", () => {
    const tool = button.dataset.tool;
    canvas.setTool(canvas.tool === tool && tool !== "select" ? "select" : tool);
  });
  if (button.dataset.tool.startsWith("add:")) {
    button.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("application/x-uml-kind", button.dataset.tool.slice(4));
      e.dataTransfer.effectAllowed = "copy";
    });
  }
});

// =====================================================================
// actions
// =====================================================================
function deleteSelection() {
  if (!canEdit || !store.selection) return;
  const sel = store.selection;
  store.update((doc) => {
    if (sel.type === "element") doc.elements = doc.elements.filter((e) => e.id !== sel.id);
    else doc.relationships = doc.relationships.filter((r) => r.id !== sel.id);
  });
  store.select(null);
  notify(sel.type === "element" ? "Element deleted — Ctrl+Z to undo." : "Relationship deleted — Ctrl+Z to undo.", "info");
}

function duplicateSelection() {
  if (!canEdit || store.selection?.type !== "element") return;
  const original = store.element(store.selection.id);
  if (original.kind === "system") return;
  const copy = JSON.parse(JSON.stringify(original));
  copy.id = store.newId("e");
  copy.x += 30;
  copy.y += 30;
  if (rules.kindsWithAttributes.includes(copy.kind)) copy.name = uniqueName(original.name.replace(/\d+$/, "") || "Copy", copy.kind);
  store.update((doc) => doc.elements.push(copy));
  store.select({ type: "element", id: copy.id });
}

function nudge(dx, dy) {
  if (!canEdit || store.selection?.type !== "element") return;
  store.update((doc) => {
    const el = doc.elements.find((e) => e.id === store.selection.id);
    el.x = Math.round(el.x + dx);
    el.y = Math.round(el.y + dy);
  });
}

function deleteDiagram() {
  window.UI.confirm({
    title: "Delete this diagram?",
    text: `“${store.meta.title}” and all its elements and relationships will be permanently deleted. This cannot be undone.`,
    onConfirm: () => {
      saver.skipPrompt = true;
      const form = $("#confirm-form");
      form.action = config.deleteUrl;
      form.submit();   // native submit: posts the CSRF-protected form
    },
  });
}

editorEl.addEventListener("delete-selection", deleteSelection);
$("#canvas").addEventListener("focus-properties", () => {
  editorEl.classList.remove("panel-hidden");
  panel.focusName();
});

// ---------------- top bar ----------------
$("#btn-undo")?.addEventListener("click", () => store.undo());
$("#btn-redo")?.addEventListener("click", () => store.redo());
$("#btn-zoom-in").addEventListener("click", () => canvas.zoomAt(1.2));
$("#btn-zoom-out").addEventListener("click", () => canvas.zoomAt(1 / 1.2));
$("#btn-zoom-reset").addEventListener("click", () => canvas.resetZoom());
$("#btn-fit").addEventListener("click", () => canvas.fit());
$("#btn-save")?.addEventListener("click", () => saver.save({ manual: true }));
$("#btn-delete-diagram")?.addEventListener("click", deleteDiagram);
$("#btn-toggle-panel").addEventListener("click", () => editorEl.classList.toggle("panel-hidden"));
$("#btn-shortcuts").addEventListener("click", () => window.UI.openModal($("#shortcuts-modal")));
document.querySelectorAll("[data-export]").forEach((b) => b.addEventListener("click", () => {
  exportDiagram(b.dataset.export, { svgEl: $("#canvas"), store, notify });
}));

titleInput.addEventListener("input", () => {
  store.setMeta("title", titleInput.value);
  if (!store.selection) {
    const field = document.querySelector('[data-meta="title"]');
    if (field) field.value = titleInput.value;
  }
});
titleInput.addEventListener("change", () => {
  const value = titleInput.value.trim();
  if (value.length < 2) {
    notify("The title must contain at least 2 characters.", "error");
    titleInput.value = data.title;
  }
  store.setMeta("title", titleInput.value.trim());
  panel.render();
});
titleInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") titleInput.blur();
  if (e.key === "Escape") { titleInput.value = store.meta.title; titleInput.blur(); }
});

// =====================================================================
// keyboard shortcuts
// =====================================================================
const toolKeys = {};
document.querySelectorAll("#toolbox .tool").forEach((b) => {
  const key = b.querySelector("kbd")?.textContent.trim().toLowerCase();
  if (key) toolKeys[key] = b.dataset.tool;
});

function typing(target) {
  return target?.closest?.("input, textarea, select, [contenteditable=true]");
}

document.addEventListener("keydown", (e) => {
  if (document.querySelector(".modal.open")) return;
  const mod = e.ctrlKey || e.metaKey;
  const key = e.key.toLowerCase();

  if (mod && key === "s") { e.preventDefault(); saver.save({ manual: true }); return; }
  if (typing(e.target)) return;

  if (mod && key === "z" && !e.shiftKey) { e.preventDefault(); if (canEdit) store.undo(); return; }
  if (mod && (key === "y" || (key === "z" && e.shiftKey))) { e.preventDefault(); if (canEdit) store.redo(); return; }
  if (mod && key === "d") { e.preventDefault(); duplicateSelection(); return; }
  if (mod) return;

  if (key === " ") { canvas.spaceDown = true; wrap.classList.add("space-pan"); e.preventDefault(); return; }
  if (key === "delete" || key === "backspace") { e.preventDefault(); deleteSelection(); return; }
  if (key === "escape") {
    if (canvas.tool !== "select") canvas.setTool("select");
    else store.select(null);
    return;
  }
  if (key.startsWith("arrow")) {
    e.preventDefault();
    const step = e.shiftKey ? 10 : 1;
    nudge(key === "arrowleft" ? -step : key === "arrowright" ? step : 0, key === "arrowup" ? -step : key === "arrowdown" ? step : 0);
    return;
  }
  if (key === "+" || key === "=") { canvas.zoomAt(1.2); return; }
  if (key === "-") { canvas.zoomAt(1 / 1.2); return; }
  if (key === "0") { canvas.resetZoom(); return; }
  if (key === "f") { canvas.fit(); return; }
  if (key === "?") { window.UI.openModal($("#shortcuts-modal")); return; }
  if (toolKeys[key]) canvas.setTool(toolKeys[key]);
});

document.addEventListener("keyup", (e) => {
  if (e.key === " ") { canvas.spaceDown = false; wrap.classList.remove("space-pan"); }
});

// =====================================================================
// start
// =====================================================================
if (!canEdit) wrap.dataset.readonly = "true";
if (window.innerWidth < 960) editorEl.classList.add("panel-hidden");   // panel is an overlay on small screens
store.on((type) => {
  if (type === "select" && store.selection && window.innerWidth < 960) editorEl.classList.remove("panel-hidden");
});
canvas.render();
panel.render();
refreshEmptyState();
refreshHistoryButtons();
requestAnimationFrame(() => {
  canvas.fit();
  $("#canvas-loading").hidden = true;
});
// re-measure text once the web fonts are available
let userMovedView = false;
wrap.addEventListener("pointerdown", () => { userMovedView = true; }, { once: true });
wrap.addEventListener("wheel", () => { userMovedView = true; }, { once: true });
document.fonts?.ready.then(() => {
  clearTextCache();
  canvas.render();
  if (!userMovedView) canvas.fit();
});

// handy for debugging from the browser console
window.__smartUml = { store, canvas, panel, saver };
