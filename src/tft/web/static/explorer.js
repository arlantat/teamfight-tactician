/** Advanced explorer: filter stored ranked boards and compare outcomes. */
import { el, button, emptyState } from "./dom.js";
import { buildsPanel } from "./explorer-builds.js";
import { ExplorerCatalog } from "./explorer-catalog.js";
import { scopeControls, tableControls } from "./explorer-controls.js";
import { createFilterBar } from "./explorer-filters.js";
import {
  addFilter,
  apiParams,
  decodeState,
  encodeState,
  firstIncludedUnit,
  refineUnit,
  rowFilter,
} from "./explorer-query.js";
import { statsTable, summaryPanel } from "./explorer-table.js";

const TAB_LABELS = {
  units: "Units",
  items: "Items",
  traits: "Traits",
  augments: "Augments",
  levels: "Levels",
  builds: "Unit builds",
};
const AUTO_MIN_SHARE = 0.005;
const DEFAULT_SORT = { key: "games", dir: "desc" };
const NATURAL_SORTS = {
  levels: { key: "level", dir: "asc" },
  stars: { key: "star", dir: "asc" },
  item_counts: { key: "item_count", dir: "asc" },
};
const ASCENDING_FIRST = new Set(["name", "avg_place", "delta"]);
const NOTE =
  "Statistics describe final boards from locally harvested ranked matches, not causes. Frequency is the share of filtered boards containing an entry; Δ compares its average placement with the filtered average (negative is better). Each board counts once per row. Small samples are noisy — raise the minimum games to focus on reliable rows.";

function routeQuery() {
  return location.hash.split("?")[1] || "";
}

export function renderExplorer(context) {
  const lookup = new ExplorerCatalog(context.catalog);
  const state = decodeState(routeQuery());
  const view = {
    search: "",
    minGames: "auto",
    splitStars: false,
    category: "",
    sorts: { ...NATURAL_SORTS },
  };
  let data = null;
  let requestNumber = 0;

  const page = el("div", "explorer-page");
  const header = el("div", "page-intro");
  const intro = el("div");
  intro.append(
    el("p", "eyebrow", "LEARN FROM THE BOARDS / EXPLORER"),
    el("h1", "", "Ask the boards anything."),
    el(
      "p",
      "page-description",
      "Combine unit, star level, item, trait, augment and level filters, then compare how every option performs on the matching ranked boards.",
    ),
  );
  header.append(intro);
  const scope = el("div", "explorer-scope");
  const filterBar = createFilterBar(lookup, (filters) => update({ filters }));
  const summary = el("div", "explorer-summary-slot");
  const results = el("div", "explorer-results");
  const status = el("p", "explorer-status");
  status.setAttribute("role", "status");
  page.append(
    header,
    scope,
    filterBar.element,
    status,
    summary,
    results,
    el("p", "data-note", NOTE),
  );

  function syncUrl() {
    const query = encodeState(state);
    history.replaceState(null, "", `#explorer${query ? `?${query}` : ""}`);
  }

  /** Apply shareable state changes, then refresh the URL and statistics. */
  function update(patch) {
    Object.assign(state, patch);
    syncUrl();
    filterBar.update(state.filters);
    load();
  }

  function renderScope() {
    scope.replaceChildren(...scopeControls(data, state, update));
  }

  function minimumGames() {
    if (view.minGames !== "auto") return Number(view.minGames);
    return Math.max(1, Math.ceil((data?.filtered.games || 0) * AUTO_MIN_SHARE));
  }

  function visible(rows) {
    const term = view.search.trim().toLowerCase();
    const minimum = minimumGames();
    return rows.filter(
      (row) =>
        row.games >= minimum &&
        (!term || row.name.toLowerCase().includes(term)) &&
        (!view.category || row.category === view.category),
    );
  }

  function table(key, rows, options) {
    return statsTable(rows, {
      ...options,
      sort: view.sorts[key] || DEFAULT_SORT,
      onSort: (column) => {
        const current = view.sorts[key] || DEFAULT_SORT;
        view.sorts[key] =
          current.key === column
            ? { key: column, dir: current.dir === "asc" ? "desc" : "asc" }
            : {
                key: column,
                dir: ASCENDING_FIRST.has(column) ? "asc" : "desc",
              };
        renderResults();
      },
    });
  }

  function addRowFilter(tab, exclude) {
    return (row) =>
      update({
        filters: addFilter(state.filters, rowFilter(tab, row, exclude)),
      });
  }

  function mainTable(tab) {
    const source =
      tab === "units" && view.splitStars ? data.unit_stars : data[tab];
    const extra =
      tab === "units"
        ? (row) => {
            const builds = button(
              "Builds",
              "explorer-row-action builds",
              () => {
                Object.assign(view, { search: "", category: "" });
                update({ focus: row.id, tab: "builds" });
              },
            );
            builds.title = `Stars, item counts and builds for ${row.name}`;
            return [builds];
          }
        : null;
    return table(tab, visible(source.map((row) => lookup.decorate(tab, row))), {
      onInclude: addRowFilter(tab, false),
      onExclude: addRowFilter(tab, true),
      extra,
      caption: `${TAB_LABELS[tab]} statistics`,
      emptyText: !data.filtered.games
        ? "No boards match these filters. Remove or loosen a filter."
        : tab === "augments" && !data.has_augments
          ? "Riot's match endpoint currently omits augment choices, so no stored boards include augments."
          : "No rows meet the minimum games for these filters.",
    });
  }

  function focusTable(key, title, rows, onInclude) {
    const section = el("section", "insight-section explorer-focus-section");
    section.append(
      el("h2", "", title),
      table(key, rows, {
        onInclude,
        caption: `${title} statistics`,
        emptyText: "No rows meet the minimum games.",
      }),
    );
    return section;
  }

  function selectTab(tab) {
    Object.assign(view, { search: "", category: "" });
    if (tab === "builds" && !state.focus) {
      const focus = firstIncludedUnit(state.filters) || data.units[0]?.id || "";
      update({ tab, focus });
      return;
    }
    state.tab = tab;
    syncUrl();
    renderResults();
  }

  function tabList() {
    const tabs = el("div", "explorer-tabs");
    tabs.setAttribute("role", "tablist");
    for (const [tab, label] of Object.entries(TAB_LABELS)) {
      const rows =
        tab === "units" && view.splitStars ? data.unit_stars : data[tab];
      const node = button(
        tab === "builds" ? label : `${label} · ${rows.length}`,
        tab === state.tab ? "selected" : "",
        () => selectTab(tab),
      );
      node.setAttribute("role", "tab");
      node.setAttribute("aria-selected", String(tab === state.tab));
      tabs.append(node);
    }
    return tabs;
  }

  function renderResults(focusSearch = false) {
    if (!data) return;
    const tab = state.tab;
    const controls = tableControls(
      tab,
      TAB_LABELS[tab],
      view,
      lookup.itemCategories(),
      (patch) => {
        Object.assign(view, patch);
        renderResults("search" in patch);
      },
    );
    const content =
      tab === "builds"
        ? buildsPanel({
            data,
            focusId: state.focus,
            lookup,
            visible,
            table: focusTable,
            onFocus: (focus) => update({ focus }),
            onRefine: (patch) =>
              update({
                filters: refineUnit(state.filters, data.focus.unit, patch),
              }),
          })
        : mainTable(tab);
    const panel = el("div", "explorer-panel");
    panel.setAttribute("role", "tabpanel");
    panel.append(controls, content);
    results.replaceChildren(tabList(), panel);
    if (focusSearch) {
      const search = controls.querySelector("input[type=search]");
      search.focus();
      search.setSelectionRange(search.value.length, search.value.length);
    }
  }

  function renderEmpty() {
    const empty = emptyState(
      "Every insight starts with a game.",
      "Harvest ranked matches with a valid Riot API key to explore boards here.",
    );
    empty.append(
      el(
        "code",
        "insight-command",
        ".venv/bin/python scripts/match_harvester.py",
      ),
      button("Check for matches", "button secondary", () => load()),
    );
    summary.replaceChildren();
    results.replaceChildren(empty);
  }

  async function load() {
    const request = ++requestNumber;
    status.textContent = "Reading your match collection…";
    page.classList.add("loading");
    try {
      const response = await fetch(`/api/explorer?${apiParams(state)}`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json().catch(() => ({}));
      if (request !== requestNumber) return;
      if (!response.ok)
        throw new Error(
          typeof payload.detail === "string"
            ? payload.detail
            : "Your local match data could not be read.",
        );
      data = payload;
      status.textContent = "";
      renderScope();
      if (!data.versions.length && !data.base.games) return renderEmpty();
      summary.replaceChildren(summaryPanel(data.base, data.filtered));
      renderResults();
    } catch (error) {
      if (request !== requestNumber) return;
      status.textContent = "";
      results.replaceChildren(
        emptyState(
          "The collection needs a moment.",
          error.message,
          button("Try again", "button secondary", () => load()),
        ),
      );
    } finally {
      if (request === requestNumber) page.classList.remove("loading");
    }
  }

  filterBar.update(state.filters);
  renderScope();
  load();
  return page;
}
