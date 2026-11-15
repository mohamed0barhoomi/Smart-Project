/*
 * Shape sizes and geometry helpers (pure functions, no DOM except text measuring).
 */
export const FONT = 'Inter, "Segoe UI", Arial, sans-serif';
export const MONO = '"JetBrains Mono", Consolas, "Courier New", monospace';

export const GRID = 10;
export const CLASS = { minW: 160, padX: 12, nameH: 30, stereoH: 14, rowH: 19, sectionPad: 6, emptySection: 10 };
export const ACTOR = { figureW: 40, figureH: 70, h: 92 };
export const SYSTEM = { minW: 220, minH: 180, defaultW: 420, defaultH: 320 };

const ctx = document.createElement("canvas").getContext("2d");
const cache = new Map();

export function textWidth(text, font) {
  const key = font + "|" + text;
  if (!cache.has(key)) {
    ctx.font = font;
    cache.set(key, ctx.measureText(text).width);
    if (cache.size > 5000) cache.clear();
  }
  return cache.get(key);
}

export function clearTextCache() { cache.clear(); }

export const nameFont = `600 13.5px ${FONT}`;
export const textFont = `400 13px ${FONT}`;
export const memberFont = `400 12px ${MONO}`;

// ---------------- UML text ----------------
export function attributeText(attr, kind) {
  if (kind === "enumeration") return attr.name;
  return `${attr.visibility} ${attr.name}${attr.data_type ? ": " + attr.data_type : ""}`;
}

export function methodText(m) {
  return `${m.visibility} ${m.name}(${m.parameters || ""})${m.return_type ? ": " + m.return_type : ""}`;
}

export function stereotype(kind) {
  if (kind === "interface") return "«interface»";
  if (kind === "enumeration") return "«enumeration»";
  return "";
}

/** Split a use case name in at most 2 balanced lines when it is long. */
export function wrapName(name) {
  if (textWidth(name, textFont) <= 190 || !name.includes(" ")) return [name];
  const words = name.split(/\s+/);
  let best = [name], bestScore = Infinity;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(" "), b = words.slice(i).join(" ");
    const score = Math.max(textWidth(a, textFont), textWidth(b, textFont));
    if (score < bestScore) { bestScore = score; best = [a, b]; }
  }
  return best;
}

// ---------------- sizes ----------------
/** Return the layout of an element: { w, h, ... } (computed from its content). */
export function measure(el) {
  switch (el.kind) {
    case "class":
    case "interface":
    case "enumeration": {
      const attrs = (el.attributes || []).map((a) => attributeText(a, el.kind));
      const methods = el.kind === "enumeration" ? [] : (el.methods || []).map(methodText);
      const widths = [
        textWidth(el.name, nameFont) + 8,
        stereotype(el.kind) ? textWidth(stereotype(el.kind), `italic 400 11px ${FONT}`) : 0,
        ...attrs.map((t) => textWidth(t, memberFont)),
        ...methods.map((t) => textWidth(t, memberFont)),
      ];
      const w = Math.ceil(Math.max(CLASS.minW, Math.max(...widths) + CLASS.padX * 2));
      const headerH = CLASS.nameH + (stereotype(el.kind) ? CLASS.stereoH : 0);
      const section = (n) => (n ? CLASS.sectionPad * 2 + n * CLASS.rowH : CLASS.emptySection);
      const attrH = section(attrs.length);
      const methH = el.kind === "enumeration" ? 0 : section(methods.length);
      return { w, h: headerH + attrH + methH, headerH, attrH, methH, attrs, methods };
    }
    case "actor": {
      const w = Math.ceil(Math.max(60, textWidth(el.name, textFont) + 12));
      return { w, h: ACTOR.h };
    }
    case "usecase": {
      const lines = wrapName(el.name);
      const tw = Math.max(...lines.map((l) => textWidth(l, textFont)));
      return { w: Math.ceil(Math.max(140, tw + 56)), h: lines.length > 1 ? 74 : 60, lines };
    }
    case "system":
      return {
        w: Math.max(SYSTEM.minW, el.width || SYSTEM.defaultW),
        h: Math.max(SYSTEM.minH, el.height || SYSTEM.defaultH),
      };
    default:
      return { w: el.width || 120, h: el.height || 60 };
  }
}

/** Store the computed sizes in the document (done before saving / exporting). */
export function applySizes(doc) {
  doc.elements.forEach((el) => {
    const m = measure(el);
    el.width = m.w;
    el.height = m.h;
  });
}

// ---------------- geometry ----------------
export function snap(value, enabled = true) {
  return enabled ? Math.round(value / GRID) * GRID : value;
}

export function center(el, m) {
  return { x: el.x + m.w / 2, y: el.y + m.h / 2 };
}

/** Shape used to clip connectors. */
function hitShape(el, m) {
  if (el.kind === "usecase") return { type: "ellipse", cx: el.x + m.w / 2, cy: el.y + m.h / 2, rx: m.w / 2, ry: m.h / 2 };
  if (el.kind === "actor") {
    const cx = el.x + m.w / 2;
    return { type: "rect", x: cx - ACTOR.figureW / 2, y: el.y, w: ACTOR.figureW, h: ACTOR.figureH };
  }
  return { type: "rect", x: el.x, y: el.y, w: m.w, h: m.h };
}

/** Anchor point of a shape (where connectors start). */
export function anchor(el, m) {
  const s = hitShape(el, m);
  return s.type === "ellipse" ? { x: s.cx, y: s.cy } : { x: s.x + s.w / 2, y: s.y + s.h / 2 };
}

/** Exit point of a ray starting at `p` (inside the shape) with direction `d`. */
export function exitPoint(el, m, p, d) {
  const s = hitShape(el, m);
  if (s.type === "ellipse") {
    const a = (d.x * d.x) / (s.rx * s.rx) + (d.y * d.y) / (s.ry * s.ry);
    const b = 2 * (((p.x - s.cx) * d.x) / (s.rx * s.rx) + ((p.y - s.cy) * d.y) / (s.ry * s.ry));
    const c = ((p.x - s.cx) ** 2) / (s.rx * s.rx) + ((p.y - s.cy) ** 2) / (s.ry * s.ry) - 1;
    const disc = b * b - 4 * a * c;
    if (a === 0 || disc < 0) return { ...p };
    const t = (-b + Math.sqrt(disc)) / (2 * a);
    return { x: p.x + d.x * t, y: p.y + d.y * t };
  }
  let t = Infinity;
  if (d.x > 0) t = Math.min(t, (s.x + s.w - p.x) / d.x);
  if (d.x < 0) t = Math.min(t, (s.x - p.x) / d.x);
  if (d.y > 0) t = Math.min(t, (s.y + s.h - p.y) / d.y);
  if (d.y < 0) t = Math.min(t, (s.y - p.y) / d.y);
  if (!isFinite(t) || t < 0) return { ...p };
  return { x: p.x + d.x * t, y: p.y + d.y * t };
}

/**
 * Compute the visible segment of a relationship.
 * `offset` shifts parallel relationships between the same two elements.
 */
export function connectorPoints(src, srcM, tgt, tgtM, offset = 0) {
  const a = anchor(src, srcM), b = anchor(tgt, tgtM);
  const dx = b.x - a.x, dy = b.y - a.y;
  const len = Math.hypot(dx, dy);
  if (len < 1) return null;
  const d = { x: dx / len, y: dy / len };
  const n = { x: -d.y, y: d.x };
  const pa = { x: a.x + n.x * offset, y: a.y + n.y * offset };
  const pb = { x: b.x + n.x * offset, y: b.y + n.y * offset };
  const start = exitPoint(src, srcM, pa, d);
  const end = exitPoint(tgt, tgtM, pb, { x: -d.x, y: -d.y });
  // overlapping shapes: nothing sensible to draw
  if ((end.x - start.x) * d.x + (end.y - start.y) * d.y <= 2) return null;
  return { start, end, d, n };
}

export function bbox(elements) {
  if (!elements.length) return null;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  elements.forEach((el) => {
    const m = measure(el);
    minX = Math.min(minX, el.x); minY = Math.min(minY, el.y);
    maxX = Math.max(maxX, el.x + m.w); maxY = Math.max(maxY, el.y + m.h);
  });
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
}

export function inside(inner, innerM, outer, outerM) {
  return inner.x >= outer.x && inner.y >= outer.y &&
    inner.x + innerM.w <= outer.x + outerM.w && inner.y + innerM.h <= outer.y + outerM.h;
}
