/** Searchable champion, trait, item and augment catalogs. */
import {
  el,
  button,
  picture,
  gold,
  icon,
  humanize,
  description,
  emptyState,
} from "./dom.js";
const TITLES = {
  champions: [
    "Meet your next carry.",
    "Explore the roster. Every champion, every possibility.",
  ],
  traits: [
    "Find your synergy.",
    "Explore the connections that bring a team together.",
  ],
  items: [
    "Make every item count.",
    "Explore equipment, component recipes, and special items.",
  ],
  augments: [
    "Change the game.",
    "Browse the augment catalog and explore your options.",
  ],
};
export function displayEntries(kind, entries) {
  if (kind !== "items") return entries;
  const grouped = new Map();
  const completeness = (item) =>
    (item.description?.trim() ? 100 : 0) +
    Object.keys(item.effects || {}).length;
  for (const item of entries) {
    const key = `${item.name.trim().toLowerCase()}:${item.category}`;
    const previous = grouped.get(key);
    if (!previous || completeness(item) > completeness(previous))
      grouped.set(key, item);
  }
  return [...grouped.values()];
}
export function championCard(champion, context, compact = false) {
  const card = el(
    "article",
    `champion-card cost-border-${Math.min(5, champion.cost)}${compact ? " compact" : ""}`,
  );
  const main = button("", "champion-card-main", () =>
    context.detail("champions", champion),
  );
  main.setAttribute(
    "aria-label",
    `View ${champion.name}, ${champion.cost} gold`,
  );
  main.append(
    picture(
      champion.icon_url || champion.square_icon_url,
      champion.name,
      "champion-art",
    ),
  );
  const text = el("span", "champion-card-text");
  const heading = el("span", "champion-card-heading");
  heading.append(el("strong", "", champion.name), gold(champion.cost));
  text.append(heading, el("small", "", champion.traits.join(" · ")));
  main.append(text);
  const add = button("+", "card-add", () => context.add(champion));
  add.title = `Add ${champion.name} to your team`;
  add.setAttribute("aria-label", add.title);
  card.append(main, add);
  return card;
}
function entityCard(kind, item, context) {
  const card = button("", `entity-card ${kind}-card`, () =>
    context.detail(kind, item),
  );
  const header = el("span", "entity-heading");
  header.append(
    picture(
      item.icon_url,
      item.name,
      kind === "traits" ? "trait-picture" : "item-picture",
    ),
  );
  const title = el("span");
  title.append(el("strong", "", item.name));
  const label =
    kind === "traits"
      ? (item.effects || []).map((effect) => effect.minUnits).join(" / ")
      : humanize(item.category || item.tier || "Augment");
  title.append(el("small", `entity-category ${item.tier || ""}`, label));
  header.append(title, icon("arrow"));
  card.append(
    header,
    el(
      "span",
      "entity-description",
      description(item.description, kind === "traits" ? {} : item.effects) ||
        "Open to explore details.",
    ),
  );
  if (kind === "traits") {
    const members = context.catalog.champions.filter((champion) =>
      champion.traits.includes(item.name),
    );
    const portraits = el("span", "trait-members-preview");
    members
      .slice(0, 7)
      .forEach((champion) =>
        portraits.append(
          picture(
            champion.square_icon_url || champion.icon_url,
            champion.name,
            "tiny-portrait",
          ),
        ),
      );
    if (members.length > 7)
      portraits.append(el("small", "", `+${members.length - 7}`));
    card.append(portraits);
  }
  if (kind === "items" && item.composition?.length) {
    const recipe = el("span", "card-recipe");
    item.composition.forEach((id, index) => {
      const component = context.catalog.items.find(
        (entry) => entry.api_name === id,
      );
      if (index) recipe.append(el("span", "", "+"));
      if (component)
        recipe.append(picture(component.icon_url, component.name, "tiny-item"));
    });
    card.append(recipe);
  }
  return card;
}
export function renderCatalog(kind, context) {
  const page = el("div", "catalog-page");
  const header = el("div", "page-intro");
  const intro = el("div");
  intro.append(
    el(
      "p",
      "eyebrow",
      `SET ${context.catalog.metadata.set_number} / ${kind.toUpperCase()}`,
    ),
    el("h1", "", TITLES[kind][0]),
    el("p", "page-description", TITLES[kind][1]),
  );
  header.append(intro);
  const controls = el("div", "catalog-controls");
  const searchWrap = el("label", "catalog-search");
  const search = el("input");
  search.type = "search";
  search.placeholder = `Search ${kind}…`;
  search.setAttribute("aria-label", `Search ${kind}`);
  searchWrap.append(icon("search"), search);
  const filter = el("select", "select");
  filter.setAttribute(
    "aria-label",
    kind === "champions"
      ? "Filter by trait"
      : kind === "items"
        ? "Filter by category"
        : "Filter by tier",
  );
  let options = [];
  if (kind === "champions")
    options = context.catalog.traits.map((trait) => trait.name).sort();
  if (kind === "items")
    options = [...new Set(context.catalog.items.map((item) => item.category))]
      .filter(Boolean)
      .sort();
  if (kind === "augments")
    options = [...new Set(context.catalog.augments.map((item) => item.tier))]
      .filter(Boolean)
      .sort();
  filter.append(
    new Option(
      kind === "champions"
        ? "All traits"
        : kind === "items"
          ? "All categories"
          : "All tiers",
      "",
    ),
  );
  options.forEach((value) => filter.append(new Option(humanize(value), value)));
  if (kind === "items" && options.includes("completed"))
    filter.value = "completed";
  const sort = el("select", "select");
  sort.setAttribute("aria-label", "Sort catalog");
  sort.append(
    new Option("Name: A–Z", "name"),
    new Option("Name: Z–A", "reverse"),
  );
  if (kind === "champions") {
    sort.append(
      new Option("Cost: low to high", "cost"),
      new Option("Cost: high to low", "cost-desc"),
    );
    sort.value = "cost";
  }
  controls.append(searchWrap);
  if (options.length) controls.append(filter);
  controls.append(sort);
  const costRow = el("div", "cost-filters");
  let selectedCost = 0;
  if (kind === "champions") {
    costRow.append(el("span", "filter-caption", "GOLD COST"));
    for (let cost = 0; cost <= 5; cost++) {
      const costButton = button(
        cost ? String(cost) : "All",
        `cost-filter${cost === 0 ? " selected" : ""}`,
        () => {
          selectedCost = cost;
          costRow.querySelectorAll("button").forEach((node) => {
            node.classList.toggle("selected", node === costButton);
            node.setAttribute("aria-pressed", String(node === costButton));
          });
          update();
        },
      );
      costButton.setAttribute("aria-pressed", String(cost === 0));
      if (cost) costButton.prepend(icon("gold"));
      costRow.append(costButton);
    }
  }
  const resultsHead = el("div", "results-heading");
  const count = el("span");
  const reset = button("Reset filters", "text-button", () => {
    search.value = "";
    filter.value = "";
    selectedCost = 0;
    costRow.querySelector("button")?.click();
    update();
  });
  resultsHead.append(count, reset);
  const results = el(
    "div",
    kind === "champions" ? "champion-grid" : "entity-grid",
  );
  const note = el(
    "p",
    "data-note",
    kind === "champions"
      ? "Includes alternate champion forms and Riftbeasts. Select a card for abilities and base stats."
      : "Descriptions come from current game data. ◇ indicates a value calculated in-game; some keyword definitions are unavailable.",
  );
  const update = () => {
    const query = search.value.trim().toLowerCase();
    let data = displayEntries(kind, context.catalog[kind]).filter((item) =>
      [item.name, ...(item.traits || []), item.description || ""]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
    if (filter.value)
      data = data.filter((item) =>
        kind === "champions"
          ? item.traits.includes(filter.value)
          : (item.category || item.tier) === filter.value,
      );
    if (selectedCost) data = data.filter((item) => item.cost === selectedCost);
    data.sort((a, b) =>
      sort.value === "cost"
        ? a.cost - b.cost || a.name.localeCompare(b.name)
        : sort.value === "cost-desc"
          ? b.cost - a.cost || a.name.localeCompare(b.name)
          : sort.value === "reverse"
            ? b.name.localeCompare(a.name)
            : a.name.localeCompare(b.name),
    );
    count.textContent = `${data.length} ${data.length === 1 ? kind.slice(0, -1) : kind}`;
    results.replaceChildren(
      ...data.map((item) =>
        kind === "champions"
          ? championCard(item, context)
          : entityCard(kind, item, context),
      ),
    );
    if (!data.length)
      results.append(
        emptyState(
          "Nothing in this clearing.",
          "Try another name or loosen your filters.",
          button("Reset filters", "button secondary", () => reset.click()),
        ),
      );
  };
  search.addEventListener("input", update);
  filter.addEventListener("change", update);
  sort.addEventListener("change", update);
  page.append(header, controls);
  if (kind === "champions") page.append(costRow);
  page.append(resultsHead, results, note);
  update();
  return page;
}
