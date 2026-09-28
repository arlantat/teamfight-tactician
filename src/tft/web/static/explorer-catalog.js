/** Case-insensitive catalog lookups and readable labels for explorer data. */
import { displayEntries } from "./catalog.js";
import { humanize } from "./dom.js";

const KINDS = {
  unit: "champions",
  item: "items",
  trait: "traits",
  augment: "augments",
};
const KIND_LABELS = {
  unit: "Unit",
  item: "Item",
  trait: "Trait",
  augment: "Augment",
  level: "Level",
};

function fallbackName(id = "") {
  return String(id)
    .replace(/^(tft\d*_|tft_|da_)/i, "")
    .replace(/^(item|augment)_/i, "")
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export class ExplorerCatalog {
  constructor(catalog) {
    this.maps = {};
    for (const [kind, collection] of Object.entries(KINDS)) {
      const entries =
        kind === "item"
          ? displayEntries("items", catalog[collection] || [])
          : catalog[collection] || [];
      this.maps[kind] = new Map(
        (catalog[collection] || []).map((entry) => [
          String(entry.api_name).toLowerCase(),
          entry,
        ]),
      );
      this[collection] = entries;
    }
  }

  entry(kind, id) {
    return this.maps[kind]?.get(String(id).toLowerCase());
  }

  name(kind, id) {
    return this.entry(kind, id)?.name?.trim() || fallbackName(id);
  }

  image(kind, id) {
    const entry = this.entry(kind, id);
    return entry?.square_icon_url || entry?.icon_url || "";
  }

  cost(id) {
    return this.entry("unit", id)?.cost || 0;
  }

  /** Unit counts for each active breakpoint, e.g. [2, 4, 6]. */
  breakpoints(id) {
    return (this.entry("trait", id)?.effects || [])
      .map((effect) => effect.minUnits)
      .filter((value) => value > 0)
      .sort((a, b) => a - b);
  }

  traitTierLabel(id, tier) {
    const count = this.breakpoints(id)[tier - 1];
    return count
      ? `${count} ${this.name("trait", id)}`
      : `${this.name("trait", id)} tier ${tier}`;
  }

  /** Search units, traits, items and augments for the add-filter picker. */
  search(query, kinds = ["unit", "trait", "item", "augment"], limit = 40) {
    const term = query.trim().toLowerCase();
    const results = [];
    for (const kind of kinds) {
      const entries = this[KINDS[kind]] || [];
      for (const entry of entries) {
        const name = entry.name?.trim() || "";
        if (term && !name.toLowerCase().includes(term)) continue;
        results.push({
          kind,
          id: String(entry.api_name).toLowerCase(),
          name,
          image: entry.square_icon_url || entry.icon_url || "",
          detail:
            kind === "unit"
              ? `${entry.cost} gold`
              : kind === "item"
                ? entry.category || ""
                : kind === "augment"
                  ? entry.tier || ""
                  : this.breakpoints(entry.api_name).join(" / "),
          rank: name.toLowerCase().startsWith(term) ? 0 : 1,
        });
      }
    }
    return results
      .sort((a, b) => a.rank - b.rank || a.name.localeCompare(b.name))
      .slice(0, limit);
  }

  /** Short human description of a simple filter. */
  describe(filter) {
    if (filter.kind === "level") {
      if (filter.max === filter.min) return `Level ${filter.min}`;
      return filter.max
        ? `Level ${filter.min}–${filter.max}`
        : `Level ${filter.min}+`;
    }
    const name = this.name(filter.kind, filter.id);
    if (filter.kind === "unit") {
      const parts = [name];
      if (filter.stars.length)
        parts.push(filter.stars.map((s) => `${s}★`).join("/"));
      if (filter.min_items) parts.push(`${filter.min_items}+ items`);
      if (filter.items.length)
        parts.push(
          `with ${filter.items.map((id) => this.name("item", id)).join(", ")}`,
        );
      return parts.join(" · ");
    }
    if (filter.kind === "item")
      return filter.min_count > 1 ? `${filter.min_count}× ${name}` : name;
    if (filter.kind === "trait") {
      const low = this.traitTierLabel(filter.id, filter.min_tier);
      if (filter.max_tier === filter.min_tier) return low;
      if (filter.max_tier)
        return `${low} – ${this.breakpoints(filter.id)[filter.max_tier - 1] || filter.max_tier}`;
      return filter.min_tier > 1 ? `${low}+` : name;
    }
    return name;
  }

  /** Add display name, image and subtitle to an API statistics row. */
  decorate(tab, row) {
    if (tab === "units") {
      const cost = this.cost(row.id);
      const gold = `${cost || "?"} gold`;
      return {
        ...row,
        name: this.name("unit", row.id),
        image: this.image("unit", row.id),
        cost,
        subtitle: row.star ? `${"★".repeat(row.star)} · ${gold}` : gold,
      };
    }
    if (tab === "items") {
      const category = this.entry("item", row.id)?.category || "";
      return {
        ...row,
        name: this.name("item", row.id),
        image: this.image("item", row.id),
        category,
        subtitle: humanize(category),
      };
    }
    if (tab === "traits")
      return {
        ...row,
        name: this.traitTierLabel(row.id, row.tier),
        image: this.image("trait", row.id),
        subtitle: `Tier ${row.tier}`,
      };
    if (tab === "augments")
      return {
        ...row,
        name: this.name("augment", row.id),
        image: this.image("augment", row.id),
        subtitle: humanize(this.entry("augment", row.id)?.tier || ""),
      };
    return { ...row, name: `Level ${row.level}`, image: "" };
  }

  /** Distinct item categories, for the items table filter. */
  itemCategories() {
    return [
      ...new Set(this.items.map((item) => item.category).filter(Boolean)),
    ].sort();
  }

  kindLabel(kind) {
    return KIND_LABELS[kind] || kind;
  }
}
