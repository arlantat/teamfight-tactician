/** Resolve reference tooltips into plain text without executing source markup. */
const MAX_DEPTH = 16;
const UNKNOWN = "variable";
const SCALE_LABELS = {
  abilitypower: "AP",
  attackdamage: "AD",
  healthmax: "max Health",
  health: "Health",
  armor: "Armor",
  magicresist: "Magic Resist",
  basicattackdamage: "attack damage",
  stack: "stacks",
  outgoingdamagemultiplier: "damage multiplier",
};
const RATIO_SCALES = new Set(["max Health", "Health", "Armor", "Magic Resist"]);

function number(value) {
  return Number.isFinite(value) ? Number(value.toFixed(3)).toString() : UNKNOWN;
}

function lookup(values, key) {
  const match = Object.keys(values || {}).find(
    (candidate) => candidate.toLowerCase() === String(key).toLowerCase(),
  );
  return match === undefined ? undefined : values[match];
}

/** Curves are step points: use the last defined value at or below this star. */
export function curveValue(points, star) {
  if (!Array.isArray(points) || !Number.isFinite(star)) return null;
  let selected = null;
  let selectedStar = -Infinity;
  for (const point of points) {
    if (
      Array.isArray(point) && Number.isFinite(point[0]) &&
      Number.isFinite(point[1]) && point[0] <= star && point[0] >= selectedStar
    ) {
      selectedStar = point[0];
      selected = point[1];
    }
  }
  return selected;
}

function starValue(values, star) {
  if (!Array.isArray(values)) return null;
  if (Array.isArray(values[0])) return curveValue(values, star);
  return Number.isFinite(values[star - 1]) ? values[star - 1] : null;
}

function mono(coefficient, factors = []) {
  return { coefficient, factors };
}

function combine(left, right, operation) {
  if (!left || operation === "override") return right;
  const simple = left.factors && right.factors;
  if (simple && operation === "multiply")
    return mono(left.coefficient * right.coefficient, [...left.factors, ...right.factors]);
  if (simple && !left.factors.length && !right.factors.length) {
    if (operation === "add") return mono(left.coefficient + right.coefficient);
    if (operation === "divide" && right.coefficient !== 0)
      return mono(left.coefficient / right.coefficient);
  }
  return { left, right, operation };
}

function calculation(id, form, star, visited = new Set()) {
  const shortId = String(id).split(".").at(-1).toLowerCase();
  if (visited.size >= MAX_DEPTH || visited.has(shortId)) return mono(1, [UNKNOWN]);
  const path = new Set(visited).add(shortId);
  const calcs = form.attribute_calcs || {};
  const key = Object.keys(calcs).find((candidate) => candidate.split(".").at(-1).toLowerCase() === shortId);
  const calc = key ? calcs[key] : null;
  if (!Array.isArray(calc?.terms) || !calc.terms.length) {
    const fallback = starValue(lookup(form.attribute_values, id), star);
    return fallback === null ? mono(1, [UNKNOWN]) : mono(fallback);
  }
  let result = null;
  for (const term of calc.terms) {
    let expression = mono(1, [UNKNOWN]);
    const value = starValue(term.type === "flat" ? term.values : term.coefficient, star);
    if (value !== null && term.type === "flat") expression = mono(value);
    if (value !== null && term.type === "scaled") {
      const scaling = String(term.scaling || "").toLowerCase();
      const label = SCALE_LABELS[scaling];
      expression = label ? mono(value, [label]) : combine(
        mono(value), calculation(term.scaling || UNKNOWN, form, star, path), "multiply",
      );
    }
    const operation = ["add", "override", "multiply", "divide"].includes(term.op) ? term.op : "add";
    result = combine(result, expression, operation);
  }
  return result || mono(1, [UNKNOWN]);
}

function expressionText(expression, percent = false) {
  if (expression.factors) {
    const { coefficient, factors } = expression;
    if (!Number.isFinite(coefficient)) return UNKNOWN;
    if (!factors.length) return `${number(coefficient)}${percent ? "%" : ""}`;
    const ratio = factors.find((factor) => RATIO_SCALES.has(factor));
    if (ratio && !percent) {
      const rest = factors.filter((factor) => factor !== ratio)
        .map((factor) => ["AP", "AD"].includes(factor) ? `${factor} scaling` : factor);
      return `${number(coefficient * 100)}% ${ratio}${rest.length ? ` × ${rest.join(" × ")}` : ""}`;
    }
    const prefix = coefficient === 1 && !percent && factors[0] === UNKNOWN ? "" : `${number(coefficient)}${percent ? "%" : ""} `;
    return `${prefix}${factors.join(" × ")}`;
  }
  const symbols = { add: "+", multiply: "×", divide: "÷" };
  const wrap = (part) => part.factors ? expressionText(part, percent) : `(${expressionText(part, percent)})`;
  return `${wrap(expression.left)} ${symbols[expression.operation] || "+"} ${wrap(expression.right)}`;
}

function formatMode(value, format = "") {
  const mode = format.toLowerCase();
  if (mode === "percentminusone") return (value - 1) * 100;
  if (mode === "invertedpercent") return (1 - value) * 100;
  if (["percent", "p"].includes(mode)) return value * 100;
  return value;
}

function isPercent(format = "") {
  return ["percent", "p", "percentminusone", "invertedpercent"].includes(format.toLowerCase());
}

/** Return a symbolic calculation, preserving health and combat dependencies. */
export function resolveAttribute(id, form = {}, star = 1, format = "") {
  let expression = calculation(id, form, star);
  if (isPercent(format)) {
    if (expression.factors && !expression.factors.length)
      expression = mono(formatMode(expression.coefficient, format));
    else if (["percent", "p"].includes(format.toLowerCase()))
      expression = combine(mono(100), expression, "multiply");
    else return `(${expressionText(expression)}) ${format.toLowerCase() === "invertedpercent" ? "inverted percentage" : "above baseline"}`;
  }
  return expressionText(expression, isPercent(format));
}

function attributes(markup) {
  const result = {};
  for (const match of markup.matchAll(/([\w]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g))
    result[match[1].toLowerCase()] = match[2] ?? match[3];
  return result;
}

function iconLabels(value = "") {
  const labels = { ap: "AP", ad: "AD", as: "Attack Speed", health: "max Health", armor: "Armor", mr: "Magic Resist", mana: "Mana" };
  return value.split(",").map((icon) => labels[icon.trim().split(".").at(-1).toLowerCase()]).filter(Boolean).join(" / ");
}

/** Render source tooltip markup as safe text for the selected star level. */
export function formatAbilityText(text = "", form = {}, star = 1) {
  return String(text || "")
    .replace(/<(script|style|iframe)\b[^>]*>[\s\S]*?<\/\1>/gi, "")
    .replace(/<TFTCurveTable\b([^>]*)>/gi, (_, markup) => {
      const attrs = attributes(markup);
      const value = curveValue(lookup(form.curve_values, attrs.row), star);
      const label = iconLabels(attrs.icon);
      return `${value === null ? UNKNOWN : number(formatMode(value, attrs.format)) + (isPercent(attrs.format) ? "%" : "")}${label ? ` ${label}` : ""}`;
    })
    .replace(/<TFTAttribute\b([^>]*)>/gi, (_, markup) => {
      const attrs = attributes(markup);
      return attrs.attributeid ? resolveAttribute(attrs.attributeid, form, star, attrs.format) : iconLabels(attrs.icon);
    })
    .replace(/<img\b([^>]*)>/gi, (_, markup) => iconLabels(attributes(markup).id))
    .replace(/<br\s*\/?\s*>/gi, "\n")
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/gi, " ").replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<").replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"').replace(/&#39;/gi, "'")
    .replace(/\\r\\n|\\n|\r\n/g, "\n")
    .replace(/\{[^}]+\}|@[^@]+@/g, UNKNOWN)
    .replace(/%i:[^%]+%/g, "")
    .replace(/[ \t]{2,}/g, " ").replace(/\n{3,}/g, "\n\n").trim();
}
