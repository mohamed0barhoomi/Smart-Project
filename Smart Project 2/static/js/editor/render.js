/*
 * SVG rendering of the diagram.  Presentation is written as SVG attributes
 * (not CSS classes) so that exported SVG/PNG files look exactly the same.
 * Everything only useful while editing carries the class "ui-only".
 */
import {
  measure, connectorPoints, stereotype, FONT, MONO, CLASS, ACTOR,
} from "./geometry.js";

const NS = "http://www.w3.org/2000/svg";
export const COLORS = {
  ink: "#334155",
  text: "#0f172a",
  muted: "#64748b",
  fill: "#ffffff",
  accent: "#2f6bd8",
  header: { class: "#eef3fc", interface: "#f1eefd", enumeration: "#ecf7f2" },
  system: "#f8fafc",
};

export function svg(tag, attrs = {}, parent = null, text = null) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v);
  }
  if (text !== null) node.textContent = text;
  if (parent) parent.appendChild(node);
  return node;
}

// ---------------- markers ----------------
export function buildMarkers(defs) {
  defs.innerHTML = "";
  [["", COLORS.ink], ["-sel", COLORS.accent]].forEach(([suffix, color]) => {
    const marker = (id, w, h, refX, path, fill) => {
      const m = svg("marker", {
        id: id + suffix, viewBox: `0 0 ${w} ${h}`, refX, refY: h / 2,
        markerWidth: w, markerHeight: h, markerUnits: "userSpaceOnUse", orient: "auto-start-reverse",
      }, defs);
      svg("path", { d: path, fill, stroke: color, "stroke-width": 1.4, "stroke-linejoin": "round" }, m);
    };
    marker("m-triangle", 14, 14, 13, "M1,1 L13,7 L1,13 Z", "#ffffff");
    marker("m-diamond", 20, 12, 19, "M1,6 L10,1 L19,6 L10,11 Z", "#ffffff");
    marker("m-diamond-filled", 20, 12, 19, "M1,6 L10,1 L19,6 L10,11 Z", color);
    marker("m-arrow", 13, 13, 12, "M1,1 L12,6.5 L1,12", "none");
  });
}

const LINE_STYLE = {
  association: { end: null, dash: null },
  inheritance: { end: "m-triangle", dash: null },
  generalization: { end: "m-triangle", dash: null },
  aggregation: { end: "m-diamond", dash: null },
  composition: { end: "m-diamond-filled", dash: null },
  dependency: { end: "m-arrow", dash: "6 4" },
  include: { end: "m-arrow", dash: "6 4", stereotype: "«include»" },
  extend: { end: "m-arrow", dash: "6 4", stereotype: "«extend»" },
};

// ---------------- text helper ----------------
function label(parent, x, y, text, opts = {}) {
  return svg("text", {
    x, y,
    "font-family": opts.mono ? MONO : FONT,
    "font-size": opts.size || 13,
    "font-weight": opts.weight || 400,
    "font-style": opts.italic ? "italic" : null,
    fill: opts.color || COLORS.text,
    "text-anchor": opts.anchor || "start",
    "dominant-baseline": "central",
    // white halo keeps labels readable on top of lines
    ...(opts.halo ? { stroke: "#ffffff", "stroke-width": 4, "stroke-linejoin": "round", "paint-order": "stroke" } : {}),
  }, parent, text);
}

// ---------------- elements ----------------
function drawClassifier(g, el, m) {
  const header = COLORS.header[el.kind];
  svg("rect", { x: 0, y: 0, width: m.w, height: m.h, rx: 4, fill: COLORS.fill, stroke: COLORS.ink, "stroke-width": 1.3 }, g);
  svg("path", {
    d: `M0,${m.headerH} V4 Q0,0 4,0 H${m.w - 4} Q${m.w},0 ${m.w},4 V${m.headerH} Z`,
    fill: header, stroke: "none",
  }, g);
  svg("rect", { x: 0, y: 0, width: m.w, height: m.h, rx: 4, fill: "none", stroke: COLORS.ink, "stroke-width": 1.3 }, g);

  let y = 15;
  const st = stereotype(el.kind);
  if (st) {
    label(g, m.w / 2, 13, st, { size: 11, italic: true, color: COLORS.muted, anchor: "middle" });
    y = 15 + CLASS.stereoH;
  }
  label(g, m.w / 2, y, el.name, { size: 13.5, weight: 600, anchor: "middle" });

  svg("line", { x1: 0, y1: m.headerH, x2: m.w, y2: m.headerH, stroke: COLORS.ink, "stroke-width": 1.1 }, g);
  m.attrs.forEach((text, i) => {
    label(g, CLASS.padX, m.headerH + CLASS.sectionPad + CLASS.rowH * i + CLASS.rowH / 2, text, { mono: true, size: 12 });
  });
  if (el.kind !== "enumeration") {
    const y2 = m.headerH + m.attrH;
    svg("line", { x1: 0, y1: y2, x2: m.w, y2: y2, stroke: COLORS.ink, "stroke-width": 1.1 }, g);
    m.methods.forEach((text, i) => {
      label(g, CLASS.padX, y2 + CLASS.sectionPad + CLASS.rowH * i + CLASS.rowH / 2, text, { mono: true, size: 12 });
    });
  }
}

function drawActor(g, el, m) {
  const cx = m.w / 2;
  const stroke = { stroke: COLORS.ink, "stroke-width": 1.6, fill: "none", "stroke-linecap": "round" };
  svg("rect", { x: cx - ACTOR.figureW / 2, y: 0, width: ACTOR.figureW, height: ACTOR.figureH, fill: "transparent", stroke: "none" }, g);
  svg("circle", { cx, cy: 11, r: 9, ...stroke, fill: COLORS.fill }, g);
  svg("path", { d: `M${cx},20 V46 M${cx - 17},29 H${cx + 17} M${cx},46 L${cx - 13},67 M${cx},46 L${cx + 13},67`, ...stroke }, g);
  label(g, cx, 82, el.name, { anchor: "middle", weight: 500 });
}

function drawUseCase(g, el, m) {
  svg("ellipse", { cx: m.w / 2, cy: m.h / 2, rx: m.w / 2, ry: m.h / 2, fill: COLORS.fill, stroke: COLORS.ink, "stroke-width": 1.3 }, g);
  const lines = m.lines;
  lines.forEach((line, i) => {
    label(g, m.w / 2, m.h / 2 + (i - (lines.length - 1) / 2) * 17, line, { anchor: "middle", weight: 500 });
  });
}

function drawSystem(g, el, m) {
  svg("rect", { x: 0, y: 0, width: m.w, height: m.h, rx: 6, fill: COLORS.system, stroke: "#94a3b8", "stroke-width": 1.3 }, g);
  label(g, 14, 18, el.name, { weight: 600, size: 13.5 });
}

function drawElement(layer, el, ctx) {
  const m = measure(el);
  const selected = ctx.selection?.type === "element" && ctx.selection.id === el.id;
  const g = svg("g", {
    class: `el el-${el.kind}${selected ? " is-selected" : ""}${ctx.connectSource === el.id ? " is-source" : ""}`,
    "data-id": el.id,
    transform: `translate(${el.x},${el.y})`,
  }, layer);

  // hover / selection outline (editor only)
  const ring = el.kind === "usecase"
    ? svg("ellipse", { cx: m.w / 2, cy: m.h / 2, rx: m.w / 2 + 5, ry: m.h / 2 + 5 })
    : svg("rect", { x: -5, y: -5, width: m.w + 10, height: m.h + 10, rx: 7 });
  ring.setAttribute("class", "ring ui-only");
  g.appendChild(ring);

  if (el.kind === "actor") drawActor(g, el, m);
  else if (el.kind === "usecase") drawUseCase(g, el, m);
  else if (el.kind === "system") drawSystem(g, el, m);
  else drawClassifier(g, el, m);

  if (selected && el.kind === "system" && ctx.canEdit) {
    svg("rect", { x: m.w - 6, y: m.h - 6, width: 12, height: 12, rx: 2, class: "resize-handle ui-only", "data-handle": "se" }, g);
  }
  return m;
}

// ---------------- relationships ----------------
function drawRelationship(layer, rel, ctx, sizes, pairIndex) {
  const src = ctx.byId.get(rel.source), tgt = ctx.byId.get(rel.target);
  if (!src || !tgt) return;
  const key = [rel.source, rel.target].sort().join("|");
  const group = pairIndex.get(key);
  const position = group.indexOf(rel.id);
  // parallel relationships between the same two elements get spread apart
  let offset = (position - (group.length - 1) / 2) * 22;
  if (rel.source > rel.target) offset = -offset;
  const pts = connectorPoints(src, sizes.get(src.id), tgt, sizes.get(tgt.id), offset);
  if (!pts) return;

  const style = LINE_STYLE[rel.rel_type] || LINE_STYLE.association;
  const selected = ctx.selection?.type === "relationship" && ctx.selection.id === rel.id;
  const color = selected ? COLORS.accent : COLORS.ink;
  const suffix = selected ? "-sel" : "";
  const g = svg("g", { class: `rel rel-${rel.rel_type}${selected ? " is-selected" : ""}`, "data-id": rel.id }, layer);
  const { start, end, d, n } = pts;
  const path = `M${start.x},${start.y} L${end.x},${end.y}`;

  svg("path", { d: path, class: "rel-hit ui-only", stroke: "transparent", "stroke-width": 14, fill: "none" }, g);
  svg("path", {
    d: path, fill: "none", stroke: color, "stroke-width": selected ? 2 : 1.4,
    "stroke-dasharray": style.dash,
    "marker-end": style.end ? `url(#${style.end}${suffix})` : null,
  }, g);

  // label (and stereotype) in the middle, on the "upper" side of the line
  const side = n.y > 0 || (n.y === 0 && n.x > 0) ? -1 : 1;
  const mid = { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };
  const texts = [style.stereotype, rel.label].filter(Boolean);
  texts.forEach((text, i) => {
    const dist = 12 + (texts.length - 1 - i) * 16;
    label(g, mid.x + n.x * side * dist, mid.y + n.y * side * dist, text, {
      anchor: "middle", size: 12, italic: text === style.stereotype, color: selected ? COLORS.accent : COLORS.muted, halo: true,
    });
  });

  // cardinalities near each end, on the other side of the line than the label
  const card = (point, dir, text) => {
    if (!text) return;
    const cs = texts.length ? -side : side;
    label(g, point.x + dir.x * 18 + n.x * cs * 11, point.y + dir.y * 18 + n.y * cs * 11, text, {
      anchor: "middle", size: 12, mono: true, color: selected ? COLORS.accent : COLORS.text, halo: true,
    });
  };
  card(start, d, rel.source_cardinality);
  card(end, { x: -d.x, y: -d.y }, rel.target_cardinality);
}

// ---------------- full render ----------------
export function renderDiagram(layers, store, ctx) {
  const { elements, relationships } = store.doc;
  Object.values(layers).forEach((layer) => layer.replaceChildren());

  const byId = new Map(elements.map((e) => [e.id, e]));
  const sizes = new Map();
  const context = { ...ctx, byId, selection: store.selection };

  // containers first (behind), then connectors, then the other elements
  elements.filter((e) => e.kind === "system").forEach((el) => sizes.set(el.id, drawElement(layers.containers, el, context)));
  elements.filter((e) => e.kind !== "system").forEach((el) => sizes.set(el.id, measure(el)));

  const pairIndex = new Map();
  relationships.forEach((rel) => {
    const key = [rel.source, rel.target].sort().join("|");
    if (!pairIndex.has(key)) pairIndex.set(key, []);
    pairIndex.get(key).push(rel.id);
  });
  relationships.forEach((rel) => drawRelationship(layers.relationships, rel, context, sizes, pairIndex));

  elements.filter((e) => e.kind !== "system").forEach((el) => drawElement(layers.elements, el, context));
  return sizes;
}
