/*
 * Persistence (autosave through the JSON API) and export (SVG, PNG, JSON).
 */
import { applySizes } from "./geometry.js";

function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/** The payload understood by diagrams.services.save_diagram_from_dict(). */
export function buildPayload(store) {
  const doc = JSON.parse(store.snapshot());
  applySizes(doc);
  return {
    title: store.meta.title,
    description: store.meta.description,
    elements: doc.elements,
    relationships: doc.relationships,
  };
}

export class Saver {
  constructor({ store, url, statusEl, notify, enabled }) {
    this.store = store;
    this.url = url;
    this.statusEl = statusEl;
    this.notify = notify;
    this.enabled = enabled;
    this.timer = null;
    this.saving = null;
    this.retry = null;
    this.lastError = null;

    window.addEventListener("beforeunload", (e) => {
      if (this.enabled && this.store.dirty && !this.skipPrompt) { e.preventDefault(); e.returnValue = ""; }
    });
  }

  setStatus(state, text) {
    this.statusEl.dataset.state = state;
    this.statusEl.querySelector(".label").textContent = text;
    this.statusEl.title = state === "error" && this.lastError ? this.lastError : "";
  }

  /** Called after each change: autosave after a short pause. */
  schedule() {
    if (!this.enabled) return;
    this.setStatus("unsaved", "Unsaved changes");
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.save(), 1500);
  }

  async save({ manual = false } = {}) {
    if (!this.enabled) return true;
    clearTimeout(this.timer);
    clearTimeout(this.retry);
    if (this.saving) {                       // a save is running: save again afterwards
      this.pending = true;
      return this.saving;
    }
    if (!this.store.dirty) {
      this.setStatus("saved", "Saved");
      if (manual) this.notify("All changes are saved.", "success");
      return true;
    }

    const version = this.store.version;
    const payload = buildPayload(this.store);
    this.setStatus("saving", "Saving…");

    this.saving = (async () => {
      try {
        const response = await fetch(this.url, {
          method: "PUT",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
          body: JSON.stringify(payload),
        });
        let data = {};
        try { data = await response.json(); } catch (_) { /* empty body */ }

        if (!response.ok) {
          const message = (data.errors && data.errors[0]) || `Save failed (${response.status}).`;
          this.lastError = message;
          this.setStatus("error", "Not saved");
          this.notify(message, "error");
          return false;
        }
        this.lastError = null;
        this.store.markSaved(version);
        if (this.store.dirty) this.setStatus("unsaved", "Unsaved changes");
        else this.setStatus("saved", "Saved");
        if (manual) this.notify("Diagram saved.", "success");
        return true;
      } catch (_) {
        this.lastError = "Network error — retrying…";
        this.setStatus("error", "Offline");
        this.retry = setTimeout(() => this.save(), 5000);
        if (manual) this.notify("Network error: the diagram will be saved when the connection is back.", "error");
        return false;
      } finally {
        this.saving = null;
        if (this.pending) { this.pending = false; this.schedule(); }
      }
    })();
    return this.saving;
  }
}

// =====================================================================
// export
// =====================================================================
function slug(text) {
  return (text || "diagram").normalize("NFKD").replace(/[^\w\s-]/g, "").trim().replace(/[\s_]+/g, "-").toLowerCase() || "diagram";
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Build a standalone SVG string of the diagram (without editor-only UI). */
export function exportSvgString(svgEl) {
  const viewport = svgEl.querySelector("#viewport");
  const layers = ["#layer-containers", "#layer-relationships", "#layer-elements"].map((s) => svgEl.querySelector(s));
  // bounding box of the real content (local coordinates of the viewport)
  let box = null;
  layers.forEach((layer) => {
    [...layer.children].forEach((child) => {
      const b = child.getBBox();
      const m = child.transform?.baseVal?.consolidate()?.matrix;
      const x = b.x + (m ? m.e : 0), y = b.y + (m ? m.f : 0);
      box = box
        ? { x1: Math.min(box.x1, x), y1: Math.min(box.y1, y), x2: Math.max(box.x2, x + b.width), y2: Math.max(box.y2, y + b.height) }
        : { x1: x, y1: y, x2: x + b.width, y2: y + b.height };
    });
  });
  if (!box) return null;
  const pad = 32;
  const x = Math.floor(box.x1 - pad), y = Math.floor(box.y1 - pad);
  const w = Math.ceil(box.x2 - box.x1 + pad * 2), h = Math.ceil(box.y2 - box.y1 + pad * 2);

  const clone = svgEl.cloneNode(true);
  clone.removeAttribute("id");
  clone.removeAttribute("class");
  clone.removeAttribute("tabindex");
  clone.removeAttribute("aria-label");
  clone.querySelectorAll(".ui-only, #layer-overlay").forEach((n) => n.remove());
  clone.querySelector("#viewport").removeAttribute("transform");
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("viewBox", `${x} ${y} ${w} ${h}`);
  clone.setAttribute("width", w);
  clone.setAttribute("height", h);
  const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  Object.entries({ x, y, width: w, height: h, fill: "#ffffff" }).forEach(([k, v]) => bg.setAttribute(k, v));
  clone.insertBefore(bg, clone.querySelector("#viewport"));
  void viewport;
  return { markup: '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone), width: w, height: h };
}

export async function exportDiagram(format, { svgEl, store, notify }) {
  const name = slug(store.meta.title);

  if (format === "json") {
    const payload = { format: "smart-uml/1", diagram_type: store.meta.diagramType, ...buildPayload(store) };
    download(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }), `${name}.json`);
    notify("JSON exported.", "success");
    return;
  }

  const result = exportSvgString(svgEl);
  if (!result) { notify("Nothing to export: the diagram is empty.", "info"); return; }

  if (format === "svg") {
    download(new Blob([result.markup], { type: "image/svg+xml" }), `${name}.svg`);
    notify("SVG exported.", "success");
    return;
  }

  // PNG: draw the SVG on a canvas at 2x for a crisp image
  const scale = 2;
  const url = URL.createObjectURL(new Blob([result.markup], { type: "image/svg+xml;charset=utf-8" }));
  try {
    const img = new Image();
    await new Promise((resolve, reject) => { img.onload = resolve; img.onerror = reject; img.src = url; });
    const canvas = document.createElement("canvas");
    canvas.width = result.width * scale;
    canvas.height = result.height * scale;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    download(blob, `${name}.png`);
    notify("PNG exported.", "success");
  } catch (_) {
    notify("PNG export failed in this browser. Try SVG instead.", "error");
  } finally {
    URL.revokeObjectURL(url);
  }
}
