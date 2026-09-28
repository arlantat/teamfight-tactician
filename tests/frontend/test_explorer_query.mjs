/** Explorer filter model and URL state regressions without a browser. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const source = await readFile(
  new URL("../../src/tft/web/static/explorer-query.js", import.meta.url),
  "utf8",
);
const query = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);

const unit = (id, extra = {}) =>
  query.normalizeSimple({ kind: "unit", id, ...extra });

test("normalizes ids, bounds values and drops invalid filters", () => {
  assert.deepEqual(
    unit(" TFT18_Ahri ", {
      stars: [3, 3, 9, 1],
      items: ["A", "", "B", "C", "D"],
      min_items: 7,
    }),
    {
      kind: "unit",
      id: "tft18_ahri",
      stars: [1, 3],
      items: ["a", "b", "c"],
      min_items: 0,
      exclude: false,
    },
  );
  assert.equal(query.normalizeSimple({ kind: "item" }), null);
  assert.equal(query.normalizeSimple({ kind: "mystery", id: "x" }), null);
  assert.deepEqual(query.normalizeSimple({ kind: "level", min: 9, max: 7 }), {
    kind: "level",
    min: 9,
    exclude: false,
  });
});

test("state round-trips through the shareable URL query", () => {
  const state = query.defaultState();
  state.filters = [
    unit("tft18_ahri", { stars: [2] }),
    { kind: "any", exclude: true, filters: [unit("a"), unit("b")] },
  ];
  state.version = "Version 16.18";
  state.focus = "tft18_ahri";
  state.tab = "builds";
  const encoded = query.encodeState(state);
  assert.match(encoded, /^q=[A-Za-z0-9_-]+$/);
  assert.deepEqual(query.decodeState(encoded), { ...state, rank: "" });
  assert.equal(query.encodeState(query.defaultState()), "");
  assert.deepEqual(query.decodeState("q=%%%"), query.defaultState());
});

test("API parameters include only chosen scope and filters", () => {
  const state = query.defaultState();
  assert.equal(query.apiParams(state).toString(), "");
  state.filters = [unit("x")];
  state.rank = "CHALLENGER";
  const params = query.apiParams(state);
  assert.deepEqual(JSON.parse(params.get("filters")), state.filters);
  assert.equal(params.get("rank"), "CHALLENGER");
});

test("row filters describe the clicked entity", () => {
  assert.deepEqual(query.rowFilter("traits", { id: "Wild", tier: 2 }), {
    kind: "trait",
    id: "wild",
    min_tier: 2,
    max_tier: 2,
    exclude: false,
  });
  assert.deepEqual(
    query.rowFilter("units", { id: "a", star: 3 }, true).stars,
    [3],
  );
  assert.deepEqual(query.rowFilter("levels", { level: 8 }), {
    kind: "level",
    min: 8,
    max: 8,
    exclude: false,
  });
});

test("adding a filter replaces its opposite instead of duplicating it", () => {
  const include = query.rowFilter("items", { id: "rod" });
  const exclude = query.rowFilter("items", { id: "rod" }, true);
  assert.deepEqual(query.addFilter([include], exclude), [exclude]);
});

test("unit refinements merge into the included unit filter", () => {
  let filters = query.refineUnit([], "A", { stars: [2] });
  filters = query.refineUnit(filters, "a", { items: ["rod"] });
  filters = query.refineUnit(filters, "a", { items: ["hat"] });
  assert.deepEqual(filters, [unit("a", { stars: [2], items: ["rod", "hat"] })]);
  filters = query.refineUnit(filters, "a", {
    items: ["x", "y"],
    replaceItems: true,
  });
  assert.deepEqual(filters[0].items, ["x", "y"]);
});

test("OR groups grow, edit and unwrap when one alternative remains", () => {
  let filters = [unit("a"), unit("b")];
  filters = query.addAlternative(filters, 0, unit("c"));
  assert.equal(filters[0].kind, "any");
  assert.deepEqual(query.filterAt(filters, [0, 1]), unit("c"));
  filters = query.updateAt(filters, [0, 1], { ...unit("c"), exclude: true });
  assert.equal(filters[0].filters[1].exclude, true);
  assert.equal(
    query.firstIncludedUnit([{ ...unit("z"), exclude: true }, ...filters]),
    "a",
  );
  filters = query.updateAt(filters, [0, 0], null);
  assert.deepEqual(filters[0], { ...unit("c"), exclude: true });
  assert.deepEqual(query.updateAt(filters, [1], null), [filters[0]]);
});

test("sorting orders numbers and names in either direction", () => {
  const rows = [
    { name: "b", games: 5, avg_place: 4.1 },
    { name: "a", games: 9, avg_place: 3.2 },
  ];
  assert.deepEqual(
    query.sortRows(rows, "avg_place", "asc").map((r) => r.name),
    ["a", "b"],
  );
  assert.deepEqual(
    query.sortRows(rows, "name", "desc").map((r) => r.name),
    ["b", "a"],
  );
  assert.deepEqual(
    query.sortRows(rows, "games", "desc").map((r) => r.games),
    [9, 5],
  );
});
