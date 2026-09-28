/** Unit drill-down: star levels, item counts, single items and full builds. */
import { el } from "./dom.js";

function focusSelect(data, focusId, lookup, onFocus) {
  const field = el("label", "explorer-inline-field");
  field.append(el("span", "", "Unit"));
  const select = el("select", "select");
  select.append(new Option("Choose a unit…", ""));
  for (const row of data.units)
    select.append(
      new Option(
        `${lookup.name("unit", row.id)} (${row.games.toLocaleString()})`,
        row.id,
      ),
    );
  select.value = focusId;
  select.addEventListener("change", () => onFocus(select.value));
  field.append(select);
  return field;
}

/**
 * Render the focus unit's breakdown. ``table(key, title, rows, onInclude)``
 * renders one sortable section; ``visible`` applies search and minimum games;
 * ``onRefine`` narrows the unit's filter.
 */
export function buildsPanel({
  data,
  focusId,
  lookup,
  visible,
  table,
  onFocus,
  onRefine,
}) {
  const wrap = el("div", "explorer-builds");
  wrap.append(focusSelect(data, focusId, lookup, onFocus));
  const focus = data.focus;
  if (!focusId || !focus) {
    wrap.append(
      el(
        "p",
        "insight-empty",
        "Choose a unit to compare its star levels, item counts, items and full builds.",
      ),
    );
    return wrap;
  }
  const unitName = lookup.name("unit", focus.unit);
  const itemName = (id) => lookup.name("item", id);
  wrap.append(
    el(
      "p",
      "explorer-focus-note",
      `${focus.games.toLocaleString()} filtered boards field ${unitName}. Frequency is the share of those boards; Δ compares with ${unitName}'s own average.`,
    ),
    table(
      "stars",
      "Star level",
      focus.stars.map((row) => ({
        ...row,
        name: `${"★".repeat(row.star)} ${unitName}`,
        image: lookup.image("unit", focus.unit),
      })),
      (row) => onRefine({ stars: [row.star] }),
    ),
    table(
      "item_counts",
      "Items held",
      focus.item_counts.map((row) => ({
        ...row,
        name: `${row.item_count} item${row.item_count === 1 ? "" : "s"}`,
        image: "",
      })),
      (row) => onRefine({ min_items: row.item_count }),
    ),
    table(
      "focus_items",
      "Items",
      visible(
        focus.items.map((row) => ({
          ...row,
          name: itemName(row.id),
          image: lookup.image("item", row.id),
        })),
      ),
      (row) => onRefine({ items: [row.id] }),
    ),
    table(
      "focus_builds",
      "Full builds",
      visible(
        focus.builds.map((row) => ({
          ...row,
          name: row.items.map(itemName).join(" + "),
          images: row.items.map((id) => ({
            url: lookup.image("item", id),
            name: itemName(id),
          })),
        })),
      ),
      (row) => onRefine({ items: row.items, replaceItems: true }),
    ),
  );
  return wrap;
}
