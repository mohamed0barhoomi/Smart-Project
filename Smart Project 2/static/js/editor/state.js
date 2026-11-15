/*
 * Editor state: the diagram document, the selection and the undo/redo history.
 *
 * Events emitted to listeners:
 *   "change" – the document changed (history entry, full refresh)
 *   "live"   – temporary change while dragging / typing (canvas refresh only)
 *   "select" – the selection changed
 *   "meta"   – title / description changed
 *   "saved"  – the document was persisted
 */
const HISTORY_LIMIT = 200;

export class Store {
  constructor(data) {
    this.meta = {
      id: data.id,
      title: data.title,
      description: data.description || "",
      diagramType: data.diagram_type,
    };
    this.doc = {
      elements: data.elements || [],
      relationships: data.relationships || [],
    };
    this.selection = null;           // { type: "element" | "relationship", id }
    this.undoStack = [];
    this.redoStack = [];
    this.version = 0;                // increases on every change
    this.savedVersion = 0;
    this.counter = 0;
    this.listeners = new Set();
  }

  // ---------------- events ----------------
  on(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  emit(type) { this.listeners.forEach((fn) => fn(type)); }

  // ---------------- ids ----------------
  newId(prefix) {
    this.counter += 1;
    return `${prefix}${Date.now().toString(36)}${this.counter}`;
  }

  // ---------------- lookups ----------------
  element(id) { return this.doc.elements.find((e) => e.id === id) || null; }
  relationship(id) { return this.doc.relationships.find((r) => r.id === id) || null; }
  relationshipsOf(elementId) {
    return this.doc.relationships.filter((r) => r.source === elementId || r.target === elementId);
  }
  selected() {
    if (!this.selection) return null;
    return this.selection.type === "element" ? this.element(this.selection.id) : this.relationship(this.selection.id);
  }

  // ---------------- history ----------------
  snapshot() { return JSON.stringify(this.doc); }

  /** Push `before` on the undo stack if the document really changed since. */
  commit(before) {
    if (before === this.snapshot()) { this.emit("change"); return false; }
    this.undoStack.push(before);
    if (this.undoStack.length > HISTORY_LIMIT) this.undoStack.shift();
    this.redoStack = [];
    this.version += 1;
    this.emit("change");
    return true;
  }

  /** Apply a mutation as one undoable step. */
  update(mutation) {
    const before = this.snapshot();
    mutation(this.doc);
    this.cleanup();
    return this.commit(before);
  }

  /** Temporary mutation (drag, typing); call commit(before) when finished. */
  live(mutation) {
    mutation(this.doc);
    this.emit("live");
  }

  /** Go back to a snapshot without creating history (used to cancel an edit). */
  restore(snapshot) {
    this.doc = JSON.parse(snapshot);
    this.fixSelection();
    this.emit("change");
  }

  undo() {
    if (!this.undoStack.length) return;
    this.redoStack.push(this.snapshot());
    this.doc = JSON.parse(this.undoStack.pop());
    this.version += 1;
    this.fixSelection();
    this.emit("change");
  }

  redo() {
    if (!this.redoStack.length) return;
    this.undoStack.push(this.snapshot());
    this.doc = JSON.parse(this.redoStack.pop());
    this.version += 1;
    this.fixSelection();
    this.emit("change");
  }

  get canUndo() { return this.undoStack.length > 0; }
  get canRedo() { return this.redoStack.length > 0; }
  get dirty() { return this.version !== this.savedVersion; }

  // ---------------- meta ----------------
  setMeta(field, value) {
    if (this.meta[field] === value) return;
    this.meta[field] = value;
    this.version += 1;
    this.emit("meta");
  }

  markSaved(version) {
    this.savedVersion = version;
    this.emit("saved");
  }

  // ---------------- selection ----------------
  select(selection) {
    const same = JSON.stringify(selection) === JSON.stringify(this.selection);
    this.selection = selection;
    if (!same) this.emit("select");
  }

  fixSelection() {
    if (this.selection && !this.selected()) this.selection = null;
  }

  /** Remove relationships whose ends no longer exist (keeps the document consistent). */
  cleanup() {
    const ids = new Set(this.doc.elements.map((e) => e.id));
    this.doc.relationships = this.doc.relationships.filter((r) => ids.has(r.source) && ids.has(r.target));
    this.fixSelection();
  }
}
