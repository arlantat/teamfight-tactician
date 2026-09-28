/** Explorer filter model, URL state, and table sorting without DOM access. */
export const TABS = [
  "units",
  "items",
  "traits",
  "augments",
  "levels",
  "builds",
];
export const MAX_FILTERS = 24;
export const MAX_ALTERNATIVES = 8;
export const MAX_UNIT_ITEMS = 3;

const DEFAULT_STATE = Object.freeze({
  filters: [],
  version: "",
  rank: "",
  focus: "",
  tab: "units",
});

export function defaultState() {
  return { ...DEFAULT_STATE, filters: [] };
}

function cleanId(value) {
  return typeof value === "string" && value.trim()
    ? value.trim().toLowerCase()
    : "";
}

function bounded(value, low, high) {
  return Number.isInteger(value) && value >= low && value <= high
    ? value
    : undefined;
}

/** Return a validated copy of one simple filter, or null when unusable. */
export function normalizeSimple(filter) {
  if (!filter || typeof filter !== "object") return null;
  const exclude = filter.exclude === true;
  if (filter.kind === "level") {
    const min = bounded(filter.min, 1, 10) ?? 1;
    const max = bounded(filter.max, min, 10);
    return { kind: "level", min, ...(max ? { max } : {}), exclude };
  }
  const id = cleanId(filter.id);
  if (!id) return null;
  if (filter.kind === "unit") {
    const stars = [...new Set(filter.stars || [])]
      .filter((star) => bounded(star, 1, 3))
      .sort();
    const items = (filter.items || [])
      .map(cleanId)
      .filter(Boolean)
      .slice(0, MAX_UNIT_ITEMS);
    const minItems = bounded(filter.min_items, 0, MAX_UNIT_ITEMS) ?? 0;
    return { kind: "unit", id, stars, items, min_items: minItems, exclude };
  }
  if (filter.kind === "item")
    return {
      kind: "item",
      id,
      min_count: bounded(filter.min_count, 1, 10) ?? 1,
      exclude,
    };
  if (filter.kind === "trait") {
    const minTier = bounded(filter.min_tier, 1, 10) ?? 1;
    const maxTier = bounded(filter.max_tier, minTier, 10);
    return {
      kind: "trait",
      id,
      min_tier: minTier,
      ...(maxTier ? { max_tier: maxTier } : {}),
      exclude,
    };
  }
  if (filter.kind === "augment") return { kind: "augment", id, exclude };
  return null;
}

/** Validate a top-level filter; OR groups of one alternative are unwrapped. */
export function normalizeFilter(filter) {
  if (filter?.kind !== "any") return normalizeSimple(filter);
  const alternatives = (filter.filters || [])
    .map(normalizeSimple)
    .filter(Boolean)
    .slice(0, MAX_ALTERNATIVES);
  if (!alternatives.length) return null;
  const exclude = filter.exclude === true;
  if (alternatives.length === 1)
    return { ...alternatives[0], exclude: alternatives[0].exclude !== exclude };
  return { kind: "any", filters: alternatives, exclude };
}

export function normalizeState(value) {
  const state = defaultState();
  if (!value || typeof value !== "object") return state;
  state.filters = (Array.isArray(value.filters) ? value.filters : [])
    .map(normalizeFilter)
    .filter(Boolean)
    .slice(0, MAX_FILTERS);
  for (const key of ["version", "rank", "focus"])
    if (typeof value[key] === "string") state[key] = value[key];
  state.focus = cleanId(state.focus);
  if (TABS.includes(value.tab)) state.tab = value.tab;
  return state;
}

function toBase64Url(text) {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  bytes.forEach((byte) => (binary += String.fromCharCode(byte)));
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function fromBase64Url(text) {
  const padded = text.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
  return new TextDecoder().decode(
    Uint8Array.from(binary, (char) => char.charCodeAt(0)),
  );
}

/** Serialize shareable state into the route's query string. */
export function encodeState(state) {
  const compact = {};
  if (state.filters.length) compact.filters = state.filters;
  for (const key of ["version", "rank", "focus"])
    if (state[key]) compact[key] = state[key];
  if (state.tab !== DEFAULT_STATE.tab) compact.tab = state.tab;
  return Object.keys(compact).length
    ? `q=${toBase64Url(JSON.stringify(compact))}`
    : "";
}

export function decodeState(query) {
  const encoded = new URLSearchParams(query || "").get("q");
  if (!encoded) return defaultState();
  try {
    return normalizeState(JSON.parse(fromBase64Url(encoded)));
  } catch {
    return defaultState();
  }
}

/** Build the request parameters understood by GET /api/explorer. */
export function apiParams(state) {
  const params = new URLSearchParams();
  if (state.filters.length)
    params.set("filters", JSON.stringify(state.filters));
  if (state.version) params.set("game_version", state.version);
  if (state.rank) params.set("rank", state.rank);
  if (state.focus) params.set("focus", state.focus);
  return params;
}

/** Create a filter describing the entity shown in a result row. */
export function rowFilter(tab, row, exclude = false) {
  if (tab === "units")
    return normalizeSimple({
      kind: "unit",
      id: row.id,
      stars: row.star ? [row.star] : [],
      exclude,
    });
  if (tab === "items")
    return normalizeSimple({ kind: "item", id: row.id, exclude });
  if (tab === "traits")
    return normalizeSimple({
      kind: "trait",
      id: row.id,
      min_tier: row.tier,
      max_tier: row.tier,
      exclude,
    });
  if (tab === "augments")
    return normalizeSimple({ kind: "augment", id: row.id, exclude });
  if (tab === "levels")
    return normalizeSimple({
      kind: "level",
      min: row.level,
      max: row.level,
      exclude,
    });
  return null;
}

/** Add a filter, replacing an identical one instead of duplicating it. */
export function addFilter(filters, filter) {
  const key = JSON.stringify({ ...filter, exclude: false });
  const rest = filters.filter(
    (entry) => JSON.stringify({ ...entry, exclude: false }) !== key,
  );
  return [...rest, filter].slice(-MAX_FILTERS);
}

/** Merge constraints into the included filter for a unit, adding one if needed. */
export function refineUnit(filters, unitId, patch) {
  const id = cleanId(unitId);
  const index = filters.findIndex(
    (entry) => entry.kind === "unit" && entry.id === id && !entry.exclude,
  );
  const current = index >= 0 ? filters[index] : { kind: "unit", id };
  const items = patch.items
    ? patch.replaceItems
      ? patch.items
      : [...(current.items || []), ...patch.items]
    : current.items;
  const merged = normalizeSimple({ ...current, ...patch, items });
  if (index < 0) return addFilter(filters, merged);
  return filters.map((entry, i) => (i === index ? merged : entry));
}

/** Append an OR alternative to the filter at ``index``. */
export function addAlternative(filters, index, alternative) {
  const target = filters[index];
  if (!target) return filters;
  const group =
    target.kind === "any"
      ? { ...target, filters: [...target.filters, alternative] }
      : { kind: "any", filters: [target, alternative], exclude: false };
  const next = normalizeFilter(group);
  return filters.map((entry, i) => (i === index ? next : entry));
}

/** Replace or remove (``replacement`` null) a filter or group alternative. */
export function updateAt(filters, path, replacement) {
  const [index, alternative] = path;
  if (alternative === undefined)
    return replacement
      ? filters.map((entry, i) => (i === index ? replacement : entry))
      : filters.filter((_, i) => i !== index);
  const group = filters[index];
  const alternatives = replacement
    ? group.filters.map((entry, i) => (i === alternative ? replacement : entry))
    : group.filters.filter((_, i) => i !== alternative);
  const next = normalizeFilter({ ...group, filters: alternatives });
  return next
    ? filters.map((entry, i) => (i === index ? next : entry))
    : filters.filter((_, i) => i !== index);
}

/** First included unit, looking inside OR groups, for the builds tab. */
export function firstIncludedUnit(filters) {
  for (const entry of filters) {
    if (entry.exclude) continue;
    const candidates = entry.kind === "any" ? entry.filters : [entry];
    const unit = candidates.find((f) => f.kind === "unit" && !f.exclude);
    if (unit) return unit.id;
  }
  return "";
}

export function filterAt(filters, path) {
  const [index, alternative] = path;
  const entry = filters[index];
  return alternative === undefined ? entry : entry?.filters?.[alternative];
}

/** Sort rows by a numeric column, keeping missing values last. */
export function sortRows(rows, key, direction) {
  const sign = direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const left = a[key];
    const right = b[key];
    if (typeof left === "string" || typeof right === "string")
      return sign * String(left ?? "").localeCompare(String(right ?? ""));
    return (
      sign * ((left ?? Infinity) - (right ?? Infinity)) || b.games - a.games
    );
  });
}
