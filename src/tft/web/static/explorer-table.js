/** Summary cards, placement histogram, and sortable statistics tables. */
import { el, button, picture } from "./dom.js";
import { sortRows } from "./explorer-query.js";

export const COLUMNS = [
  { key: "name", label: "Name", align: "left" },
  { key: "games", label: "Games", title: "Boards containing this entry" },
  { key: "frequency", label: "Freq", title: "Share of the filtered boards" },
  {
    key: "avg_place",
    label: "Avg place",
    title: "Average placement (lower is better)",
  },
  {
    key: "delta",
    label: "Δ",
    title: "Average placement minus the filtered average",
  },
  { key: "top4", label: "Top 4", title: "Top-four rate" },
  { key: "win", label: "Win", title: "First-place rate" },
];

export const percent = (value) =>
  value === null || value === undefined ? "—" : `${(value * 100).toFixed(1)}%`;
export const place = (value) =>
  value === null || value === undefined ? "—" : value.toFixed(2);
export function signed(value) {
  if (value === null || value === undefined) return "—";
  const rounded = Number(value.toFixed(2));
  return `${rounded > 0 ? "+" : rounded < 0 ? "−" : "±"}${Math.abs(rounded).toFixed(2)}`;
}

function deltaClass(value) {
  if (value <= -0.15) return "delta-good";
  if (value >= 0.15) return "delta-bad";
  return "delta-even";
}

function stat(label, value, note, className = "") {
  const card = el("div", `explorer-stat ${className}`);
  card.append(el("small", "", label), el("strong", "", value));
  if (note) card.append(el("span", "", note));
  return card;
}

/** Headline outcome of the filtered boards compared with the scope. */
export function summaryPanel(base, filtered) {
  const panel = el("section", "explorer-summary");
  panel.setAttribute("aria-label", "Filtered boards summary");
  const share = base.games ? filtered.games / base.games : 0;
  const delta =
    filtered.avg_place !== null && base.avg_place !== null
      ? filtered.avg_place - base.avg_place
      : null;
  const cards = el("div", "explorer-stats");
  cards.append(
    stat(
      "Boards",
      filtered.games.toLocaleString(),
      `${percent(share)} of ${base.games.toLocaleString()}`,
    ),
    stat(
      "Avg place",
      place(filtered.avg_place),
      delta === null ? "" : `${signed(delta)} vs all`,
      delta === null ? "" : deltaClass(delta),
    ),
    stat("Top 4", percent(filtered.top4), `all: ${percent(base.top4)}`),
    stat("Win", percent(filtered.win), `all: ${percent(base.win)}`),
  );
  panel.append(cards, histogram(filtered));
  return panel;
}

function histogram(summary) {
  const chart = el("div", "explorer-histogram");
  chart.setAttribute("role", "img");
  const peak = Math.max(1, ...summary.placements);
  const shares = summary.placements.map((count) =>
    summary.games ? count / summary.games : 0,
  );
  chart.setAttribute(
    "aria-label",
    `Placement distribution: ${shares.map((share, i) => `${i + 1}${["st", "nd", "rd"][i] || "th"} ${percent(share)}`).join(", ")}`,
  );
  summary.placements.forEach((count, index) => {
    const column = el("div", `explorer-bar${index < 4 ? " top" : ""}`);
    column.title = `${index + 1}: ${count.toLocaleString()} boards (${percent(shares[index])})`;
    const fill = el("span", "explorer-bar-fill");
    fill.style.height = `${(count / peak) * 100}%`;
    column.append(
      el("small", "", percent(shares[index]).replace(".0%", "%")),
      fill,
      el("strong", "", index + 1),
    );
    chart.append(column);
  });
  return chart;
}

/**
 * Render a sortable table. Rows need ``name`` plus the statistic columns;
 * ``row.image`` and ``row.subtitle`` decorate the name cell.
 */
export function statsTable(rows, options) {
  const { sort, onSort, onInclude, onExclude, extra, caption, emptyText } =
    options;
  if (!rows.length)
    return el(
      "p",
      "insight-empty",
      emptyText || "No boards match these filters.",
    );
  const wrap = el("div", "insight-table-wrap explorer-table-wrap");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", caption);
  const table = el("table", "insight-table explorer-table");
  const head = el("tr");
  for (const column of COLUMNS) {
    const th = el("th", column.align === "left" ? "" : "numeric");
    th.scope = "col";
    const active = sort.key === column.key;
    th.setAttribute(
      "aria-sort",
      active ? (sort.dir === "asc" ? "ascending" : "descending") : "none",
    );
    const control = button(
      `${column.label}${active ? (sort.dir === "asc" ? " ▲" : " ▼") : ""}`,
      "explorer-sort",
      () => onSort(column.key),
    );
    if (column.title) control.title = column.title;
    th.append(control);
    head.append(th);
  }
  head.append(el("th", "explorer-actions-head"));
  const thead = el("thead");
  thead.append(head);
  const body = el("tbody");
  for (const row of sortRows(rows, sort.key, sort.dir)) {
    const tr = el("tr");
    const name = el("td", "explorer-name");
    const label = onInclude
      ? button("", "explorer-name-button", () => onInclude(row))
      : el("span", "explorer-name-button");
    if (onInclude) label.title = "Add as filter";
    if (row.images)
      row.images.forEach((image) =>
        label.append(picture(image.url, image.name, "explorer-row-icon")),
      );
    else
      label.append(
        picture(
          row.image,
          row.name,
          `explorer-row-icon${row.cost ? ` cost-border-${Math.min(5, row.cost)}` : ""}`,
        ),
      );
    const text = el("span", "explorer-name-text");
    text.append(el("strong", "", row.name));
    if (row.subtitle) text.append(el("small", "", row.subtitle));
    label.append(text);
    name.append(label);
    tr.append(
      name,
      el("td", "numeric", row.games.toLocaleString()),
      el("td", "numeric muted", percent(row.frequency)),
      el("td", "numeric strong", place(row.avg_place)),
      el("td", `numeric ${deltaClass(row.delta)}`, signed(row.delta)),
      el("td", "numeric", percent(row.top4)),
      el("td", "numeric", percent(row.win)),
    );
    const actions = el("td", "explorer-row-actions");
    if (onInclude) {
      const include = button("+", "explorer-row-action", () => onInclude(row));
      include.title = `Only boards with ${row.name}`;
      include.setAttribute("aria-label", include.title);
      actions.append(include);
    }
    if (onExclude) {
      const exclude = button("−", "explorer-row-action exclude", () =>
        onExclude(row),
      );
      exclude.title = `Only boards without ${row.name}`;
      exclude.setAttribute("aria-label", exclude.title);
      actions.append(exclude);
    }
    if (extra) actions.append(...extra(row));
    tr.append(actions);
    body.append(tr);
  }
  table.append(thead, body);
  wrap.append(table);
  return wrap;
}
