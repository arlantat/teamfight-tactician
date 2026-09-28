/** Scope selectors and per-table controls for the explorer. */
import { el, humanize } from "./dom.js";

export const MIN_GAME_OPTIONS = [
  ["Auto", "auto"],
  ["Any", "1"],
  ["10+", "10"],
  ["25+", "25"],
  ["50+", "50"],
  ["100+", "100"],
  ["250+", "250"],
];

function labelledSelect(className, label, options, value, onChoose) {
  const field = el("label", className);
  field.append(el("span", "", label));
  const node = el("select", "select");
  options.forEach(([text, optionValue]) =>
    node.append(new Option(text, optionValue)),
  );
  node.value = value;
  node.addEventListener("change", () => onChoose(node.value));
  field.append(node);
  return field;
}

/** Game version and rank selectors applied before any filter. */
export function scopeControls(data, state, onChange) {
  const versions = data?.versions || [];
  const ranks = data?.ranks || [];
  return [
    labelledSelect(
      "insight-version",
      "Game version",
      [["All stored versions", ""], ...versions.map((v) => [v, v])],
      state.version,
      (version) => onChange({ version }),
    ),
    labelledSelect(
      "insight-version",
      "Rank",
      [
        ["All ranks", ""],
        ...ranks.map((rank) => [humanize(rank.toLowerCase()), rank]),
      ],
      state.rank,
      (rank) => onChange({ rank }),
    ),
  ];
}

/**
 * Search, minimum games, and tab-specific options. ``onChange`` receives the
 * changed view fields.
 */
export function tableControls(tab, label, view, categories, onChange) {
  const controls = el("div", "explorer-table-controls");
  const search = el("input");
  search.type = "search";
  search.placeholder = `Search ${label.toLowerCase()}…`;
  search.setAttribute("aria-label", search.placeholder);
  search.value = view.search;
  search.addEventListener("input", () => onChange({ search: search.value }));
  controls.append(
    search,
    labelledSelect(
      "explorer-inline-field",
      "Min games",
      MIN_GAME_OPTIONS,
      view.minGames,
      (minGames) => onChange({ minGames }),
    ),
  );
  if (tab === "units") {
    const split = el("label", "explorer-toggle");
    const box = el("input");
    box.type = "checkbox";
    box.checked = view.splitStars;
    box.addEventListener("change", () => onChange({ splitStars: box.checked }));
    split.append(box, el("span", "", "Split by star level"));
    controls.append(split);
  }
  if (tab === "items")
    controls.append(
      labelledSelect(
        "explorer-inline-field",
        "Category",
        [["All", ""], ...categories.map((value) => [humanize(value), value])],
        view.category,
        (category) => onChange({ category }),
      ),
    );
  return controls;
}
