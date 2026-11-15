/*
 * Right sidebar: properties of the selection (or of the diagram).
 *
 * Inputs carry `data-path` (property path on the selected object).  Typing
 * updates the canvas live; the change becomes ONE undo step when the field
 * is committed (blur / Enter).  Invalid values are rolled back.
 */
import { attributeText, methodText } from "./geometry.js";

const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const icon = (name) => `<svg class="icon"><use href="#i-${name}"></use></svg>`;

function getPath(obj, path) { return path.split(".").reduce((o, k) => (o == null ? o : o[k]), obj); }
function setPath(obj, path, value) {
  const keys = path.split(".");
  const last = keys.pop();
  const target = keys.reduce((o, k) => o[k], obj);
  target[last] = value;
}

export class Panel {
  constructor({ root, store, rules, canEdit, factory, notify, onMetaChange }) {
    this.root = root;
    this.store = store;
    this.rules = rules;
    this.canEdit = canEdit;
    this.factory = factory;
    this.notify = notify;
    this.onMetaChange = onMetaChange;
    this.before = null;
    this.cardRegex = new RegExp(rules.cardinalityRegex);
    this.bind();
  }

  // =============== helpers ===============
  current(doc = this.store.doc) {
    const sel = this.store.selection;
    if (!sel) return null;
    const list = sel.type === "element" ? doc.elements : doc.relationships;
    return list.find((x) => x.id === sel.id) || null;
  }

  disabled() { return this.canEdit ? "" : "disabled"; }

  visibilitySelect(path, value) {
    return `<select class="vis-select" data-path="${path}" ${this.disabled()} title="Visibility" aria-label="Visibility">
      ${this.rules.visibilities.map(([v, label]) => `<option value="${v}" ${v === value ? "selected" : ""} title="${label}">${v}</option>`).join("")}
    </select>`;
  }

  kindLabel(kind) { return this.rules.elementKindLabels[kind] || kind; }
  relLabel(type) { return this.rules.relationshipLabels[type] || type; }

  // =============== rendering ===============
  render() {
    // remember focus so re-rendering does not interrupt the user
    const active = document.activeElement;
    const focusKey = this.root.contains(active) ? active.dataset.key : null;
    const caret = focusKey && "selectionStart" in active ? [active.selectionStart, active.selectionEnd] : null;

    const sel = this.store.selection;
    const obj = this.current();
    if (!sel || !obj) this.root.innerHTML = this.diagramHtml();
    else if (sel.type === "element") this.root.innerHTML = this.elementHtml(obj);
    else this.root.innerHTML = this.relationshipHtml(obj);

    if (focusKey) {
      const field = this.root.querySelector(`[data-key="${CSS.escape(focusKey)}"]`);
      if (field) {
        field.focus({ preventScroll: true });
        if (caret && field.setSelectionRange) { try { field.setSelectionRange(...caret); } catch (_) { /* number inputs */ } }
      }
    }
  }

  header(iconName, title, subtitle, deleteAction) {
    return `<div class="prop-header">
      <span class="prop-icon">${icon(iconName)}</span>
      <div class="prop-heading"><p class="prop-kicker">${esc(subtitle)}</p><h2>${esc(title)}</h2></div>
      ${this.canEdit && deleteAction ? `<button type="button" class="icon-btn icon-btn-sm danger-hover" data-action="${deleteAction}" title="Delete (Del)" aria-label="Delete">${icon("trash")}</button>` : ""}
    </div>`;
  }

  field(label, inner, hint = "") {
    return `<label class="prop-field"><span class="prop-label">${label}</span>${inner}${hint ? `<span class="prop-hint">${hint}</span>` : ""}</label>`;
  }

  input(path, value, opts = {}) {
    return `<input type="${opts.type || "text"}" class="prop-input${opts.mono ? " mono" : ""}" data-path="${path}" data-key="${path}"
      value="${esc(value)}" ${opts.required ? "data-required" : ""} ${opts.lazy ? "data-lazy" : ""} ${opts.kind ? `data-kind="${opts.kind}"` : ""}
      ${opts.placeholder ? `placeholder="${esc(opts.placeholder)}"` : ""} ${opts.list ? `list="${opts.list}"` : ""}
      maxlength="${opts.max || 120}" ${this.disabled()} aria-label="${esc(opts.label || path)}">`;
  }

  // ---------- diagram (nothing selected) ----------
  diagramHtml() {
    const { elements, relationships } = this.store.doc;
    const meta = this.store.meta;
    const groups = {};
    elements.forEach((e) => { (groups[e.kind] ||= []).push(e); });
    const outline = Object.entries(groups).map(([kind, items]) => `
      <p class="outline-title">${esc(this.kindLabel(kind))} <span>${items.length}</span></p>
      ${items.map((e) => `<button type="button" class="outline-item" data-action="select-element" data-id="${esc(e.id)}">${icon(e.kind)}<span>${esc(e.name)}</span></button>`).join("")}
    `).join("");

    return `
      ${this.header("info", "Diagram", "Properties", null)}
      <div class="prop-section">
        ${this.field("Title", `<input type="text" class="prop-input" data-meta="title" data-key="meta-title" value="${esc(meta.title)}" maxlength="120" ${this.disabled()} aria-label="Title">`)}
        ${this.field("Description", `<textarea class="prop-input" data-meta="description" data-key="meta-description" rows="3" maxlength="1000" ${this.disabled()} placeholder="Describe this diagram…">${esc(meta.description)}</textarea>`)}
        <div class="prop-stats">
          <div><strong>${elements.length}</strong><span>Elements</span></div>
          <div><strong>${relationships.length}</strong><span>Relationships</span></div>
        </div>
      </div>
      <div class="prop-section">
        <p class="prop-section-title">Outline</p>
        ${outline || `<p class="prop-empty">No elements yet.</p>`}
      </div>
      ${this.canEdit ? `<div class="prop-section prop-tips">
        <p class="prop-section-title">Tips</p>
        <ul>
          <li>Drag a shape from the toolbox onto the canvas.</li>
          <li>Pick a relationship, click the source, then the target.</li>
          <li>Hold <kbd>Shift</kbd> to keep a tool active.</li>
          <li>Hold <kbd>Alt</kbd> while dragging to move freely (no grid).</li>
        </ul>
      </div>` : ""}`;
  }

  // ---------- element ----------
  elementHtml(el) {
    const isClassifier = this.rules.kindsWithAttributes.includes(el.kind);
    let html = this.header(el.kind, el.name, this.kindLabel(el.kind), "delete-selection");

    html += `<div class="prop-section">`;
    html += this.field("Name", this.input("name", el.name, { required: true, label: "Name" }));
    if (isClassifier) {
      const kinds = this.rules.kindsWithAttributes;
      html += this.field("Type", `<div class="seg" role="radiogroup">${kinds.map((k) => `
        <button type="button" class="seg-btn ${k === el.kind ? "active" : ""}" data-action="set-kind" data-kind="${k}" ${this.disabled()}>${esc(this.kindLabel(k))}</button>`).join("")}</div>`);
    }
    if (el.kind !== "system") {
      html += this.field(isClassifier ? "Notes" : "Description",
        `<textarea class="prop-input" data-path="description" data-key="description" rows="${el.kind === "usecase" ? 3 : 2}" maxlength="2000" ${this.disabled()} placeholder="${el.kind === "usecase" ? "Goal, main scenario…" : "Optional"}">${esc(el.description)}</textarea>`);
    }
    html += `</div>`;

    if (isClassifier) {
      const isEnum = el.kind === "enumeration";
      html += `<div class="prop-section">
        <div class="prop-section-head"><p class="prop-section-title">${isEnum ? "Literals" : "Attributes"} <span>${el.attributes.length}</span></p>
        ${this.canEdit ? `<button type="button" class="btn btn-ghost btn-xs" data-action="add-attribute">${icon("plus")} Add</button>` : ""}</div>
        <div class="members">
        ${el.attributes.map((a, i) => `
          <div class="member" title="${esc(attributeText(a, el.kind))}">
            ${isEnum ? "" : this.visibilitySelect(`attributes.${i}.visibility`, a.visibility)}
            ${this.input(`attributes.${i}.name`, a.name, { required: true, mono: true, placeholder: isEnum ? "LITERAL" : "name", label: "Attribute name" })}
            ${isEnum ? "" : this.input(`attributes.${i}.data_type`, a.data_type, { mono: true, placeholder: "type", label: "Data type", list: "type-suggestions" })}
            ${this.canEdit ? `<button type="button" class="icon-btn icon-btn-xs" data-action="remove-attribute" data-index="${i}" title="Remove" aria-label="Remove attribute">${icon("x")}</button>` : ""}
          </div>`).join("") || `<p class="prop-empty">No ${isEnum ? "literals" : "attributes"}.</p>`}
        </div>
      </div>`;

      if (this.rules.kindsWithMethods.includes(el.kind)) {
        html += `<div class="prop-section">
          <div class="prop-section-head"><p class="prop-section-title">Methods <span>${el.methods.length}</span></p>
          ${this.canEdit ? `<button type="button" class="btn btn-ghost btn-xs" data-action="add-method">${icon("plus")} Add</button>` : ""}</div>
          <div class="members">
          ${el.methods.map((m, i) => `
            <div class="member member-method" title="${esc(methodText(m))}">
              <div class="member-line">
                ${this.visibilitySelect(`methods.${i}.visibility`, m.visibility)}
                ${this.input(`methods.${i}.name`, m.name, { required: true, mono: true, placeholder: "name", label: "Method name" })}
                ${this.canEdit ? `<button type="button" class="icon-btn icon-btn-xs" data-action="remove-method" data-index="${i}" title="Remove" aria-label="Remove method">${icon("x")}</button>` : ""}
              </div>
              <div class="member-line member-sub">
                <span class="paren">(</span>${this.input(`methods.${i}.parameters`, m.parameters, { mono: true, placeholder: "params", label: "Parameters", max: 255 })}<span class="paren">):</span>
                ${this.input(`methods.${i}.return_type`, m.return_type, { mono: true, placeholder: "void", label: "Return type", list: "type-suggestions" })}
              </div>
            </div>`).join("") || `<p class="prop-empty">No methods.</p>`}
          </div>
        </div>`;
      }
    }

    if (el.kind !== "system") html += this.relationsOfHtml(el);

    html += `<div class="prop-section">
      <p class="prop-section-title">Position</p>
      <div class="prop-grid">
        ${this.field("X", this.input("x", Math.round(el.x), { type: "number", kind: "number", label: "X" }))}
        ${this.field("Y", this.input("y", Math.round(el.y), { type: "number", kind: "number", label: "Y" }))}
      </div>
    </div>
    <datalist id="type-suggestions">${["int", "float", "double", "bool", "boolean", "str", "String", "char", "Date", "DateTime", "void", "List", "Map", "Set"].map((t) => `<option value="${t}">`).join("")}</datalist>`;
    return html;
  }

  relationsOfHtml(el) {
    const rels = this.store.relationshipsOf(el.id);
    const name = (id) => this.store.element(id)?.name || "?";
    return `<div class="prop-section">
      <p class="prop-section-title">Relationships <span>${rels.length}</span></p>
      ${rels.map((r) => {
        const outgoing = r.source === el.id;
        return `<button type="button" class="rel-item" data-action="select-relationship" data-id="${esc(r.id)}">
          ${icon("rel-" + r.rel_type)}
          <span><strong>${esc(this.relLabel(r.rel_type))}</strong> ${outgoing ? "to" : "from"} ${esc(name(outgoing ? r.target : r.source))}${r.label ? ` · <em>${esc(r.label)}</em>` : ""}</span>
        </button>`;
      }).join("") || `<p class="prop-empty">Not connected.</p>`}
    </div>`;
  }

  // ---------- relationship ----------
  relationshipHtml(rel) {
    const types = this.rules.relationshipTypes[this.store.meta.diagramType];
    const source = this.store.element(rel.source), target = this.store.element(rel.target);
    const connectable = this.store.doc.elements.filter((e) => !this.rules.nonConnectableKinds.includes(e.kind));
    const isClass = this.store.meta.diagramType === "class";

    const endpointSelect = (path, value) => `<select class="prop-input" data-path="${path}" data-key="${path}" ${this.disabled()}>
      ${connectable.map((e) => `<option value="${esc(e.id)}" ${e.id === value ? "selected" : ""}>${esc(e.name)} (${esc(this.kindLabel(e.kind))})</option>`).join("")}
    </select>`;

    const typeOptions = types.map((t) => {
      const err = this.factory.relationshipError(t, source, target, rel.id);
      return `<option value="${t}" ${t === rel.rel_type ? "selected" : ""} ${err && t !== rel.rel_type ? "disabled" : ""}>${esc(this.relLabel(t))}</option>`;
    }).join("");

    const directionHint = {
      inheritance: "The source inherits from the target.",
      generalization: "The source is a specialisation of the target.",
      aggregation: "The diamond is drawn on the target (the whole).",
      composition: "The filled diamond is drawn on the target (the whole).",
      dependency: "The source depends on the target.",
      include: "The source use case includes the target.",
      extend: "The source use case extends the target.",
      association: "",
    }[rel.rel_type];

    let html = this.header("rel-" + rel.rel_type, this.relLabel(rel.rel_type), "Relationship", "delete-selection");
    html += `<div class="prop-section">
      ${this.field("Type", `<select class="prop-input" data-path="rel_type" data-key="rel_type" ${this.disabled()}>${typeOptions}</select>`, directionHint)}
      ${this.field("Source", endpointSelect("source", rel.source))}
      ${this.canEdit ? `<button type="button" class="btn btn-ghost btn-xs swap-btn" data-action="swap">${icon("swap")} Swap direction</button>` : ""}
      ${this.field("Target", endpointSelect("target", rel.target))}
      ${this.field("Label", this.input("label", rel.label, { placeholder: rel.rel_type === "association" ? "e.g. places" : "Optional", label: "Label" }))}
    </div>`;
    if (isClass) {
      html += `<div class="prop-section">
        <p class="prop-section-title">Cardinality</p>
        <div class="prop-grid">
          ${this.field(`At ${esc(source?.name || "source")}`, this.input("source_cardinality", rel.source_cardinality, { mono: true, lazy: true, kind: "cardinality", placeholder: "—", list: "card-suggestions", max: 20, label: "Source cardinality" }))}
          ${this.field(`At ${esc(target?.name || "target")}`, this.input("target_cardinality", rel.target_cardinality, { mono: true, lazy: true, kind: "cardinality", placeholder: "—", list: "card-suggestions", max: 20, label: "Target cardinality" }))}
        </div>
        <div class="chips">${this.rules.cardinalitySuggestions.map((c) => `<span class="chip">${esc(c)}</span>`).join("")}</div>
        <datalist id="card-suggestions">${this.rules.cardinalitySuggestions.map((c) => `<option value="${esc(c)}">`).join("")}</datalist>
      </div>`;
    }
    return html;
  }

  // =============== events ===============
  bind() {
    const root = this.root;

    root.addEventListener("focusin", (e) => {
      if (e.target.matches("[data-path], [data-meta]")) this.before = this.store.snapshot();
    });

    root.addEventListener("input", (e) => {
      const t = e.target;
      if (t.dataset.meta) {
        this.store.setMeta(t.dataset.meta, t.value);
        this.onMetaChange?.(t.dataset.meta, t.value);
        return;
      }
      if (!t.dataset.path || t.hasAttribute("data-lazy") || t.tagName === "SELECT") return;
      const value = t.dataset.kind === "number" ? Number(t.value) : t.value;
      if (t.dataset.kind === "number" && (t.value === "" || !isFinite(value))) return;
      this.store.live((doc) => setPath(this.current(doc), t.dataset.path, value));
    });

    root.addEventListener("change", (e) => this.commitField(e.target));

    root.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.matches("input[data-path], input[data-meta]")) {
        e.preventDefault();
        e.target.blur();
      }
      if (e.key === "Escape" && e.target.matches("[data-path]") && this.before) {
        this.store.restore(this.before);   // cancel the edit
        this.before = null;
        e.target.blur();
        e.stopPropagation();
      }
    });

    root.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-action]");
      if (btn && !btn.disabled) this.action(btn.dataset.action, btn);
      const chip = e.target.closest(".chip");
      if (chip && this.canEdit) {
        // fill the focused (or first empty) cardinality input
        const inputs = [...root.querySelectorAll('[data-kind="cardinality"]')];
        const field = inputs.find((i) => i === this.lastCardinality) || inputs.find((i) => !i.value) || inputs[1];
        if (field) {
          this.before = this.store.snapshot();
          field.value = chip.textContent;
          this.commitField(field);
        }
      }
    });
    root.addEventListener("focusout", (e) => {
      if (e.target.dataset.kind === "cardinality") this.lastCardinality = e.target;
    });
  }

  commitField(t) {
    if (t.dataset.meta) {
      if (t.dataset.meta === "title" && t.value.trim().length < 2) {
        this.notify("The title must contain at least 2 characters.", "error");
        t.value = this.store.meta.title.trim().length >= 2 ? this.store.meta.title : "Untitled diagram";
      }
      this.store.setMeta(t.dataset.meta, t.value.trim());
      this.onMetaChange?.(t.dataset.meta, t.value.trim());
      return;
    }
    if (!t.dataset.path) return;
    const before = this.before || this.store.snapshot();
    const path = t.dataset.path;
    let value = t.value;

    const fail = (message) => {
      this.notify(message, "error");
      this.store.restore(before);
      this.before = this.store.snapshot();
    };

    if (t.dataset.kind === "number") {
      value = Number(value);
      if (t.value === "" || !isFinite(value)) return fail("Please enter a number.");
    } else {
      value = value.trim();
    }
    if (t.hasAttribute("data-required") && !value) return fail("This field cannot be empty.");
    if (t.dataset.kind === "cardinality" && value && !this.cardRegex.test(value)) {
      return fail("Invalid cardinality. Use 1, 0..1, *, 0..* or 1..*.");
    }

    const sel = this.store.selection;
    const obj = this.current();
    if (!obj) return;

    // element name must stay unique among classifiers
    if (sel.type === "element" && path === "name" && this.rules.kindsWithAttributes.includes(obj.kind)) {
      const clash = this.store.doc.elements.some((e) => e.id !== obj.id && this.rules.kindsWithAttributes.includes(e.kind) && e.name.toLowerCase() === value.toLowerCase());
      if (clash) return fail(`A classifier named “${value}” already exists.`);
    }

    // relationship type / ends must respect the UML rules
    if (sel.type === "relationship" && ["rel_type", "source", "target"].includes(path)) {
      const next = { ...obj, [path]: value };
      const err = this.factory.relationshipError(next.rel_type, this.store.element(next.source), this.store.element(next.target), obj.id);
      if (err) return fail(err);
      if (path === "rel_type" && this.store.meta.diagramType !== "class") { next.source_cardinality = ""; next.target_cardinality = ""; }
    }

    setPath(obj, path, value);
    this.store.commit(before);
    this.before = this.store.snapshot();
  }

  action(name, btn) {
    const store = this.store;
    const sel = store.selection;
    const withCurrent = (fn) => store.update((doc) => fn(this.current(doc), doc));

    switch (name) {
      case "select-element":
        store.select({ type: "element", id: btn.dataset.id });
        break;
      case "select-relationship":
        store.select({ type: "relationship", id: btn.dataset.id });
        break;
      case "delete-selection":
        this.root.dispatchEvent(new CustomEvent("delete-selection", { bubbles: true }));
        break;
      case "set-kind": {
        const kind = btn.dataset.kind;
        withCurrent((el) => {
          if (el.kind === kind) return;
          if (kind === "enumeration" && el.methods.length) {
            el.methods = [];
            this.notify("Methods were removed: enumerations only have literals.", "info");
          }
          el.kind = kind;
        });
        break;
      }
      case "add-attribute":
        withCurrent((el) => {
          const isEnum = el.kind === "enumeration";
          el.attributes.push({ name: isEnum ? `VALUE${el.attributes.length + 1}` : `attribute${el.attributes.length + 1}`, data_type: isEnum ? "" : "String", visibility: "-" });
        });
        this.focusLast("attributes", "name");
        break;
      case "remove-attribute":
        withCurrent((el) => el.attributes.splice(Number(btn.dataset.index), 1));
        break;
      case "add-method":
        withCurrent((el) => el.methods.push({ name: `method${el.methods.length + 1}`, parameters: "", return_type: "void", visibility: "+" }));
        this.focusLast("methods", "name");
        break;
      case "remove-method":
        withCurrent((el) => el.methods.splice(Number(btn.dataset.index), 1));
        break;
      case "swap":
        if (sel?.type === "relationship") {
          const rel = this.current();
          const err = this.factory.relationshipError(rel.rel_type, store.element(rel.target), store.element(rel.source), rel.id);
          if (err) { this.notify(err, "error"); break; }
          withCurrent((r) => {
            [r.source, r.target] = [r.target, r.source];
            [r.source_cardinality, r.target_cardinality] = [r.target_cardinality, r.source_cardinality];
          });
        }
        break;
      default:
        break;
    }
  }

  focusLast(listName, field) {
    const inputs = this.root.querySelectorAll(`[data-path^="${listName}."][data-path$=".${field}"]`);
    const last = inputs[inputs.length - 1];
    if (last) { last.focus(); last.select(); }
  }

  focusName() {
    const input = this.root.querySelector('[data-path="name"], [data-path="label"]');
    if (input) { input.focus(); input.select(); }
  }
}
