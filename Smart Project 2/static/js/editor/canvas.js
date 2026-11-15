/*
 * Canvas interactions: zoom, pan, selection, drag & drop, element placement,
 * relationship creation and system boundary resizing.
 */
import { renderDiagram, buildMarkers, svg } from "./render.js";
import { measure, snap, bbox, inside, anchor, SYSTEM } from "./geometry.js";

const MIN_ZOOM = 0.2, MAX_ZOOM = 3;

export class Canvas {
  constructor({ svgEl, wrap, store, rules, canEdit, factory, notify, onToolChange }) {
    this.svg = svgEl;
    this.wrap = wrap;
    this.store = store;
    this.rules = rules;
    this.canEdit = canEdit;
    this.factory = factory;          // creates new elements / relationships
    this.notify = notify;            // (message, type) -> toast
    this.onToolChange = onToolChange;
    this.viewport = svgEl.querySelector("#viewport");
    this.layers = {
      containers: svgEl.querySelector("#layer-containers"),
      relationships: svgEl.querySelector("#layer-relationships"),
      elements: svgEl.querySelector("#layer-elements"),
    };
    this.overlay = svgEl.querySelector("#layer-overlay");
    this.view = { x: 0, y: 0, k: 1 };
    this.tool = "select";
    this.connectSource = null;
    this.action = null;              // current pointer action
    this.spaceDown = false;
    this.listeners = new Set();

    buildMarkers(svgEl.querySelector("#canvas-defs"));
    this.bindEvents();
  }

  onViewChange(fn) { this.listeners.add(fn); }

  // =============== rendering ===============
  render() {
    this.sizes = renderDiagram(this.layers, this.store, {
      canEdit: this.canEdit,
      connectSource: this.connectSource,
    });
    this.wrap.classList.toggle("is-connecting", this.tool.startsWith("connect:"));
  }

  // =============== view ===============
  applyView() {
    const { x, y, k } = this.view;
    this.viewport.setAttribute("transform", `translate(${x},${y}) scale(${k})`);
    const size = 20 * k;
    this.wrap.style.backgroundSize = `${size}px ${size}px, ${size * 5}px ${size * 5}px, ${size * 5}px ${size * 5}px`;
    this.wrap.style.backgroundPosition = `${x}px ${y}px`;
    this.listeners.forEach((fn) => fn(this.view));
  }

  toWorld(clientX, clientY) {
    const r = this.svg.getBoundingClientRect();
    return { x: (clientX - r.left - this.view.x) / this.view.k, y: (clientY - r.top - this.view.y) / this.view.k };
  }

  zoomAt(factor, clientX, clientY) {
    const r = this.svg.getBoundingClientRect();
    const cx = clientX ?? r.left + r.width / 2;
    const cy = clientY ?? r.top + r.height / 2;
    const k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, this.view.k * factor));
    const px = cx - r.left, py = cy - r.top;
    this.view.x = px - ((px - this.view.x) * k) / this.view.k;
    this.view.y = py - ((py - this.view.y) * k) / this.view.k;
    this.view.k = k;
    this.applyView();
  }

  resetZoom() { this.zoomAt(1 / this.view.k); }

  fit() {
    const box = bbox(this.store.doc.elements);
    const r = this.svg.getBoundingClientRect();
    if (!box || !r.width) {
      this.view = { x: r.width / 2 - 200, y: 80, k: 1 };
      return this.applyView();
    }
    const pad = 60;
    const k = Math.min(1.2, Math.max(MIN_ZOOM, Math.min((r.width - pad * 2) / box.w, (r.height - pad * 2) / box.h)));
    this.view = {
      k,
      x: (r.width - box.w * k) / 2 - box.x * k,
      y: (r.height - box.h * k) / 2 - box.y * k,
    };
    this.applyView();
  }

  /** Center of the visible area in world coordinates. */
  visibleCenter() {
    const r = this.svg.getBoundingClientRect();
    return this.toWorld(r.left + r.width / 2, r.top + r.height / 2);
  }

  // =============== tools ===============
  setTool(tool) {
    if (!this.canEdit && tool !== "select" && tool !== "pan") return;
    this.tool = tool;
    this.connectSource = null;
    this.clearOverlay();
    this.wrap.dataset.tool = tool.split(":")[0];
    this.render();
    this.onToolChange?.(tool);
  }

  clearOverlay() { this.overlay.replaceChildren(); }

  // =============== hit testing ===============
  hit(target) {
    const handle = target.closest?.("[data-handle]");
    if (handle) return { type: "handle", id: handle.closest(".el").dataset.id };
    const el = target.closest?.(".el");
    if (el) return { type: "element", id: el.dataset.id };
    const rel = target.closest?.(".rel");
    if (rel) return { type: "relationship", id: rel.dataset.id };
    return null;
  }

  // =============== events ===============
  bindEvents() {
    const s = this.svg;
    s.addEventListener("pointerdown", (e) => this.pointerDown(e));
    window.addEventListener("pointermove", (e) => this.pointerMove(e));
    window.addEventListener("pointerup", (e) => this.pointerUp(e));
    s.addEventListener("dblclick", (e) => {
      const hit = this.hit(e.target);
      if (hit?.type === "element" || hit?.type === "relationship") this.svg.dispatchEvent(new CustomEvent("focus-properties", { bubbles: true }));
    });
    s.addEventListener("wheel", (e) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        this.zoomAt(Math.exp(-e.deltaY * 0.0022), e.clientX, e.clientY);
      } else {
        this.view.x -= e.shiftKey ? e.deltaY : e.deltaX;
        this.view.y -= e.shiftKey ? 0 : e.deltaY;
        this.applyView();
      }
    }, { passive: false });

    // drag & drop from the toolbox
    this.wrap.addEventListener("dragover", (e) => {
      if (this.canEdit && e.dataTransfer.types.includes("application/x-uml-kind")) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "copy";
      }
    });
    this.wrap.addEventListener("drop", (e) => {
      const kind = e.dataTransfer.getData("application/x-uml-kind");
      if (!kind || !this.canEdit) return;
      e.preventDefault();
      this.addElement(kind, this.toWorld(e.clientX, e.clientY));
    });

    window.addEventListener("resize", () => this.applyView());
  }

  pointerDown(e) {
    if (e.button === 2) return;
    this.svg.focus({ preventScroll: true });
    const world = this.toWorld(e.clientX, e.clientY);
    const hit = this.hit(e.target);

    // panning: middle button, space key or pan tool
    if (e.button === 1 || this.spaceDown || this.tool === "pan") {
      return this.startPan(e);
    }

    if (this.tool.startsWith("add:")) {
      this.addElement(this.tool.slice(4), world, true);
      if (!e.shiftKey) this.setTool("select");
      return;
    }

    if (this.tool.startsWith("connect:")) {
      return this.connectClick(hit, world, e);
    }

    // select tool
    if (hit?.type === "handle" && this.canEdit) {
      const el = this.store.element(hit.id);
      this.action = { type: "resize", id: el.id, before: this.store.snapshot(), start: world, w: measure(el).w, h: measure(el).h };
      return;
    }
    if (hit?.type === "element") {
      this.store.select({ type: "element", id: hit.id });
      if (this.canEdit) {
        const el = this.store.element(hit.id);
        // dragging a system boundary also moves the elements inside it
        const carried = [];
        if (el.kind === "system") {
          const m = measure(el);
          this.store.doc.elements.forEach((other) => {
            if (other.id !== el.id && other.kind !== "system" && inside(other, measure(other), el, m)) {
              carried.push({ id: other.id, x: other.x, y: other.y });
            }
          });
        }
        this.action = { type: "move", id: el.id, before: this.store.snapshot(), start: world, x: el.x, y: el.y, carried, moved: false };
      }
      return;
    }
    if (hit?.type === "relationship") {
      this.store.select({ type: "relationship", id: hit.id });
      return;
    }
    this.store.select(null);
    this.startPan(e);
  }

  startPan(e) {
    this.action = { type: "pan", sx: e.clientX, sy: e.clientY, x: this.view.x, y: this.view.y };
    this.wrap.classList.add("is-panning");
  }

  pointerMove(e) {
    const a = this.action;
    if (this.tool.startsWith("connect:") && this.connectSource) this.drawRubberBand(this.toWorld(e.clientX, e.clientY));
    if (!a) return;

    if (a.type === "pan") {
      this.view.x = a.x + e.clientX - a.sx;
      this.view.y = a.y + e.clientY - a.sy;
      this.applyView();
      return;
    }

    const world = this.toWorld(e.clientX, e.clientY);
    const dx = world.x - a.start.x, dy = world.y - a.start.y;

    if (a.type === "move") {
      if (!a.moved && Math.hypot(dx, dy) < 3 / this.view.k) return;
      a.moved = true;
      const useSnap = !e.altKey;
      this.store.live((doc) => {
        const el = doc.elements.find((x) => x.id === a.id);
        el.x = snap(a.x + dx, useSnap);
        el.y = snap(a.y + dy, useSnap);
        const realDx = el.x - a.x, realDy = el.y - a.y;
        a.carried.forEach((c) => {
          const other = doc.elements.find((x) => x.id === c.id);
          if (other) { other.x = c.x + realDx; other.y = c.y + realDy; }
        });
      });
    }

    if (a.type === "resize") {
      this.store.live((doc) => {
        const el = doc.elements.find((x) => x.id === a.id);
        el.width = Math.max(SYSTEM.minW, snap(a.w + dx));
        el.height = Math.max(SYSTEM.minH, snap(a.h + dy));
      });
    }
  }

  pointerUp() {
    const a = this.action;
    this.action = null;
    this.wrap.classList.remove("is-panning");
    if (!a) return;
    if ((a.type === "move" && a.moved) || a.type === "resize") this.store.commit(a.before);
  }

  // =============== creation ===============
  addElement(kind, world, centered = true) {
    const el = this.factory.element(kind);
    const m = measure(el);
    el.x = snap(centered ? world.x - m.w / 2 : world.x);
    el.y = snap(centered ? world.y - m.h / 2 : world.y);
    this.store.update((doc) => { doc.elements.push(el); });
    this.store.select({ type: "element", id: el.id });
    return el;
  }

  connectClick(hit, world, e) {
    const type = this.tool.slice(8);
    if (!hit || hit.type !== "element") {
      if (this.connectSource) { this.connectSource = null; this.clearOverlay(); this.render(); this.onToolChange?.(this.tool); }
      else this.notify("Click on the source element first.", "info");
      return;
    }
    const el = this.store.element(hit.id);
    if (this.rules.nonConnectableKinds.includes(el.kind)) {
      this.notify("A system boundary cannot be connected.", "error");
      return;
    }
    if (!this.connectSource) {
      const pairs = this.rules.relationshipEndpoints[this.store.meta.diagramType][type];
      if (pairs && !pairs.some(([s]) => s === el.kind)) {
        const label = this.rules.relationshipLabels[type];
        this.notify(`${label} cannot start from ${this.rules.elementKindLabels[el.kind].toLowerCase()}.`, "error");
        return;
      }
      this.connectSource = el.id;
      this.render();
      this.drawRubberBand(world);
      this.onToolChange?.(this.tool);
      return;
    }
    const source = this.store.element(this.connectSource);
    const error = this.factory.relationshipError(type, source, el);
    if (error) { this.notify(error, "error"); return; }
    const rel = this.factory.relationship(type, source.id, el.id);
    this.connectSource = null;
    this.clearOverlay();
    this.store.update((doc) => { doc.relationships.push(rel); });
    this.store.select({ type: "relationship", id: rel.id });
    if (!e.shiftKey) this.setTool("select");
  }

  drawRubberBand(world) {
    const source = this.store.element(this.connectSource);
    if (!source) return;
    const a = anchor(source, measure(source));
    this.clearOverlay();
    svg("line", { x1: a.x, y1: a.y, x2: world.x, y2: world.y, class: "rubber-band" }, this.overlay);
  }
}
