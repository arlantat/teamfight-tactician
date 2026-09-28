/** Editor panel for one filter or OR-group alternative. */
import { el, button, picture } from "./dom.js";
import { picker } from "./explorer-picker.js";
import {
  MAX_ALTERNATIVES,
  MAX_UNIT_ITEMS,
  addAlternative,
  filterAt,
  normalizeSimple,
  updateAt,
} from "./explorer-query.js";

const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

export function newFilter(option) {
  if (option.kind === "level")
    return normalizeSimple({ kind: "level", min: 8 });
  return normalizeSimple({ kind: option.kind, id: option.id });
}

function segmented(label, options, value, onChoose) {
  const group = el("div", "explorer-field");
  group.append(el("span", "explorer-field-label", label));
  const row = el("div", "explorer-segmented");
  row.setAttribute("role", "group");
  row.setAttribute("aria-label", label);
  for (const [text, optionValue] of options) {
    const on = Array.isArray(value)
      ? value.includes(optionValue)
      : value === optionValue;
    const node = button(text, on ? "selected" : "", () =>
      onChoose(optionValue),
    );
    node.setAttribute("aria-pressed", String(on));
    row.append(node);
  }
  group.append(row);
  return group;
}

function select(label, options, value, onChoose) {
  const field = el("label", "explorer-field");
  field.append(el("span", "explorer-field-label", label));
  const node = el("select", "select");
  options.forEach(([text, optionValue]) =>
    node.append(new Option(text, String(optionValue))),
  );
  node.value = String(value ?? "");
  node.addEventListener("change", () =>
    onChoose(node.value === "" ? undefined : Number(node.value)),
  );
  field.append(node);
  return field;
}

function kindFields(lookup, filter, update) {
  const fields = [];
  if (filter.kind === "unit") {
    fields.push(
      segmented(
        "Star level",
        [
          ["1★", 1],
          ["2★", 2],
          ["3★", 3],
        ],
        filter.stars,
        (star) =>
          update({
            stars: filter.stars.includes(star)
              ? filter.stars.filter((s) => s !== star)
              : [...filter.stars, star],
          }),
      ),
      segmented(
        "Items held",
        [
          ["Any", 0],
          ["1+", 1],
          ["2+", 2],
          ["3", 3],
        ],
        filter.min_items,
        (count) => update({ min_items: count }),
      ),
    );
    const items = el("div", "explorer-field");
    items.append(el("span", "explorer-field-label", "Holding items"));
    const held = el("div", "explorer-held-items");
    filter.items.forEach((id, index) => {
      const itemChip = button("", "explorer-held-item", () =>
        update({ items: filter.items.filter((_, i) => i !== index) }),
      );
      itemChip.title = `Remove ${lookup.name("item", id)}`;
      itemChip.append(
        picture(
          lookup.image("item", id),
          lookup.name("item", id),
          "explorer-chip-icon",
        ),
        el("span", "", lookup.name("item", id)),
        el("span", "explorer-held-x", "×"),
      );
      held.append(itemChip);
    });
    if (filter.items.length < MAX_UNIT_ITEMS)
      held.append(
        picker(lookup, {
          placeholder: "Add an item…",
          kinds: ["item"],
          onPick: (option) => update({ items: [...filter.items, option.id] }),
        }),
      );
    items.append(held);
    fields.push(items);
  } else if (filter.kind === "item") {
    fields.push(
      segmented(
        "Copies on board",
        [
          ["1+", 1],
          ["2+", 2],
          ["3+", 3],
          ["4+", 4],
        ],
        filter.min_count,
        (count) => update({ min_count: count }),
      ),
    );
  } else if (filter.kind === "trait") {
    const tiers = lookup.breakpoints(filter.id);
    const options = (tiers.length ? tiers : [1, 2, 3, 4]).map(
      (count, index) => [
        tiers.length ? `${count} units` : `Tier ${index + 1}`,
        index + 1,
      ],
    );
    fields.push(
      select("Minimum", options, filter.min_tier, (tier) =>
        update({
          min_tier: tier,
          max_tier:
            filter.max_tier && filter.max_tier < tier ? tier : filter.max_tier,
        }),
      ),
      select(
        "Maximum",
        [["Any", ""], ...options.filter(([, tier]) => tier >= filter.min_tier)],
        filter.max_tier,
        (tier) => update({ max_tier: tier }),
      ),
    );
  } else if (filter.kind === "level") {
    const options = LEVELS.map((level) => [String(level), level]);
    fields.push(
      select("Minimum", options, filter.min, (min) =>
        update({ min, max: filter.max && filter.max < min ? min : filter.max }),
      ),
      select(
        "Maximum",
        [["Any", ""], ...options.filter(([, level]) => level >= filter.min)],
        filter.max,
        (max) => update({ max }),
      ),
    );
  }
  return fields;
}

/**
 * Render the editor for ``selected`` ([index] or [index, alternative]).
 * ``choose`` changes the edited path, ``setAdding`` toggles the alternative
 * picker, and ``commit`` applies new filters with the next selection.
 */
export function editorPanel(lookup, view) {
  const { filters, selected, addingAlternative, choose, setAdding, commit } =
    view;
  if (!selected) return null;
  const target = filterAt(filters, selected);
  if (!target) return null;
  const [index, alternative] = selected;
  const group = filters[index];
  const panel = el("div", "explorer-editor");
  const head = el("div", "explorer-editor-head");
  head.append(
    el(
      "strong",
      "",
      target.kind === "any"
        ? "Any of these"
        : `${lookup.kindLabel(target.kind)} · ${lookup.describe(target)}`,
    ),
  );
  const close = button("Done", "text-button", () => choose(null));
  head.append(close);
  panel.append(head);
  if (group.kind === "any") {
    const alternatives = el("div", "explorer-alternatives");
    const top = button(
      "Group",
      alternative === undefined ? "selected" : "",
      () => choose([index]),
    );
    alternatives.append(top);
    group.filters.forEach((entry, i) => {
      const node = button(
        lookup.describe(entry),
        i === alternative ? "selected" : "",
        () => choose([index, i]),
      );
      if (entry.exclude) node.classList.add("excluded");
      alternatives.append(node);
    });
    panel.append(alternatives);
  }
  const fields = el("div", "explorer-editor-fields");
  fields.append(
    segmented(
      "Match",
      [
        ["Include", false],
        ["Exclude", true],
      ],
      target.exclude,
      (exclude) => commit(updateAt(filters, selected, { ...target, exclude })),
    ),
  );
  if (target.kind !== "any")
    fields.append(
      ...kindFields(lookup, target, (patch) =>
        commit(
          updateAt(filters, selected, normalizeSimple({ ...target, ...patch })),
        ),
      ),
    );
  panel.append(fields);
  const actions = el("div", "explorer-editor-actions");
  const size = group.kind === "any" ? group.filters.length : 1;
  if (addingAlternative)
    actions.append(
      picker(lookup, {
        placeholder: "Alternative unit, trait, item, augment or level…",
        kinds: ["unit", "trait", "item", "augment", "level"],
        autofocus: true,
        onPick: (option) =>
          commit(addAlternative(filters, index, newFilter(option)), [index]),
      }),
    );
  else if (size < MAX_ALTERNATIVES)
    actions.append(
      button("+ Add OR alternative", "button secondary compact", () =>
        setAdding(true),
      ),
    );
  actions.append(
    button(
      alternative === undefined ? "Remove filter" : "Remove alternative",
      "button ghost compact danger",
      () => commit(updateAt(filters, selected, null), null),
    ),
  );
  panel.append(actions);
  return panel;
}
