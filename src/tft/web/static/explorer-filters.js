/** Filter chips and the filter bar that hosts the picker and editor. */
import { el, button, picture } from "./dom.js";
import { editorPanel, newFilter } from "./explorer-editor.js";
import { picker } from "./explorer-picker.js";
import {
  MAX_FILTERS,
  addFilter,
  filterAt,
  updateAt,
} from "./explorer-query.js";

function chip(lookup, filter, selected, onSelect, onRemove) {
  const node = el(
    "div",
    `explorer-chip kind-${filter.kind}${filter.exclude ? " excluded" : ""}${selected ? " selected" : ""}`,
  );
  const main = button("", "explorer-chip-main", onSelect);
  main.setAttribute("aria-pressed", String(selected));
  if (filter.exclude) main.append(el("span", "explorer-chip-not", "NOT"));
  if (filter.kind === "any") {
    main.append(el("span", "explorer-chip-kind", "ANY OF"));
    filter.filters.forEach((alternative, index) => {
      if (index) main.append(el("span", "explorer-chip-or", "or"));
      main.append(
        el(
          "span",
          alternative.exclude
            ? "explorer-chip-alt excluded"
            : "explorer-chip-alt",
          `${alternative.exclude ? "not " : ""}${lookup.describe(alternative)}`,
        ),
      );
    });
  } else {
    if (filter.id)
      main.append(
        picture(
          lookup.image(filter.kind, filter.id),
          lookup.name(filter.kind, filter.id),
          "explorer-chip-icon",
        ),
      );
    main.append(el("span", "", lookup.describe(filter)));
  }
  const remove = button("×", "explorer-chip-remove", onRemove);
  remove.setAttribute("aria-label", "Remove filter");
  node.append(main, remove);
  return node;
}

/** Filter bar component; ``update`` re-renders it from explorer state. */
export function createFilterBar(lookup, onChange) {
  const root = el("section", "explorer-filters");
  root.setAttribute("aria-label", "Board filters");
  let filters = [];
  let selected = null;
  let addingAlternative = false;
  const commit = (next, nextSelected = selected) => {
    selected = nextSelected;
    addingAlternative = false;
    onChange(next);
  };

  function editor() {
    return editorPanel(lookup, {
      filters,
      selected,
      addingAlternative,
      choose: (path) => {
        selected = path;
        addingAlternative = false;
        render();
      },
      setAdding: (value) => {
        addingAlternative = value;
        render();
      },
      commit,
    });
  }

  function render() {
    const row = el("div", "explorer-filter-row");
    filters.forEach((filter, index) => {
      const isSelected = selected?.[0] === index;
      row.append(
        chip(
          lookup,
          filter,
          isSelected,
          () => {
            selected = isSelected && selected.length === 1 ? null : [index];
            addingAlternative = false;
            render();
          },
          () => commit(updateAt(filters, [index], null), null),
        ),
      );
    });
    if (filters.length < MAX_FILTERS)
      row.append(
        picker(lookup, {
          placeholder: filters.length
            ? "Add filter…"
            : "Filter by unit, trait, item, augment or level…",
          kinds: ["unit", "trait", "item", "augment", "level"],
          onPick: (option) => {
            const next = addFilter(filters, newFilter(option));
            commit(
              next,
              option.kind === "unit" ||
                option.kind === "trait" ||
                option.kind === "level"
                ? [next.length - 1]
                : null,
            );
          },
        }),
      );
    if (filters.length)
      row.append(
        button("Clear all", "text-button explorer-clear", () =>
          commit([], null),
        ),
      );
    const panel = editor();
    root.replaceChildren(row, ...(panel ? [panel] : []));
  }

  return {
    element: root,
    update(nextFilters) {
      filters = nextFilters;
      if (selected && !filterAt(filters, selected)) selected = null;
      render();
    },
  };
}
