/** Editorial overview composed entirely from the current catalog. */
import { el, link, icon, picture, sectionHeading, button } from "./dom.js";
import { championCard, displayEntries } from "./catalog.js";
import { renderNewsPreview } from "./notes.js";

export function renderOverview(catalog, context) {
  const page = el("div", "overview-page");
  const intro = el("div", "page-intro");
  const introText = el("div");
  introText.append(
    el("p", "eyebrow", "EVERY GREAT TEAM STARTS WITH AN IDEA"),
    el("h1", "", "Welcome to the wilds."),
  );
  const setTag = el(
    "span",
    "outline-tag",
    `SET ${catalog.metadata.set_number} FIELD GUIDE`,
  );
  setTag.prepend(icon("leaf"));
  intro.append(introText, setTag);
  const hero = el("section", "hero");
  hero.setAttribute("aria-label", "Enchanted Wilds");
  const art = el("img", "hero-art");
  art.src = "/static/assets/characters.webp";
  art.alt =
    "Lux and the creatures of TFT Enchanted Wilds, official Riot Games artwork";
  const heroText = el("div", "hero-content");
  const badge = el(
    "span",
    "hero-badge",
    `SET ${catalog.metadata.set_number}${catalog.metadata.patch ? ` · PATCH ${catalog.metadata.patch}` : ""}`,
  );
  heroText.append(
    badge,
    el("h2", "", catalog.metadata.set_name),
    el(
      "p",
      "",
      "Wild magic. Endless possibilities.\nDiscover your champions, find your synergies, and bring your next team to life.",
    ),
  );
  const actions = el("div", "hero-actions");
  const build = link("Build a team", "#builder", "button primary");
  build.append(icon("arrow"));
  actions.append(
    build,
    link("Explore champions", "#champions", "button ghost"),
  );
  heroText.append(actions);
  hero.append(art, heroText, el("span", "hero-caption", "FIGHT TO FLOURISH"));
  const stats = el("div", "catalog-stats");
  for (const [key, label, copy] of [
    ["champions", "Champions", "Meet your next carry"],
    ["traits", "Traits", "Find the connections"],
    ["items", "Items", "Equip for the moment"],
    ["augments", "Augments", "Discover your options"],
  ]) {
    const item = link("", `#${key}`, "catalog-stat");
    const text = el("div");
    text.append(
      el("span", "stat-label", label),
      el("strong", "", displayEntries(key, catalog[key]).length),
      el("span", "stat-copy", copy),
    );
    item.append(icon(key), text, icon("arrow", "stat-arrow"));
    stats.append(item);
  }
  page.append(intro, hero, stats);
  const lower = el("div", "overview-lower");
  const left = el("section", "featured-champions");
  left.append(
    sectionHeading(
      "MEET THE ROSTER",
      "A world of possibilities",
      "#champions",
      "All champions",
    ),
  );
  const cards = el("div", "featured-grid");
  const chosen = ["Ahri", "Lillia", "Ashe", "Morgana", "Ivern", "Gnar"];
  for (const name of chosen) {
    const champion = catalog.champions.find((item) => item.name === name);
    if (champion) cards.append(championCard(champion, context));
  }
  left.append(cards);
  const right = el("section", "trait-preview");
  right.append(
    sectionHeading(
      "BETTER TOGETHER",
      "Follow your nature",
      "#traits",
      "All traits",
    ),
  );
  const list = el("div", "trait-preview-list");
  for (const name of ["Elderwood", "Blossom", "Coven", "Fae"]) {
    const trait = catalog.traits.find((item) => item.name === name);
    if (!trait) continue;
    const row = button("", "trait-preview-row", () =>
      context.detail("traits", trait),
    );
    const text = el("span", "trait-row-text");
    text.append(
      el("strong", "", name),
      el(
        "small",
        "",
        `${catalog.champions.filter((champion) => champion.traits.includes(name)).length} champions · ${(trait.effects || []).map((effect) => effect.minUnits).join(" / ")}`,
      ),
    );
    row.append(
      picture(trait.icon_url, name, "trait-picture"),
      text,
      icon("arrow"),
    );
    list.append(row);
  }
  right.append(list);
  lower.append(left, right);
  const banner = el("section", "builder-banner");
  const bannerText = el("div");
  bannerText.append(
    el("p", "eyebrow", "YOUR BOARD. YOUR POSSIBILITIES."),
    el("h2", "", "Let your next idea take root."),
    el(
      "p",
      "",
      "Arrange your champions and watch your traits come together. Your team is saved on this device.",
    ),
  );
  const bannerLink = link("Open team builder", "#builder", "button secondary");
  bannerLink.append(icon("arrow"));
  banner.append(icon("builder", "banner-icon"), bannerText, bannerLink);
  const note = el("p", "data-note");
  const updated = new Date(catalog.metadata.fetched_at);
  note.textContent = `Catalog refreshed ${Number.isNaN(updated.getTime()) ? "recently" : updated.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}. Counts include champion forms and special items. Explore the catalog for details.`;
  page.append(intro, hero, stats, renderNewsPreview(context.news), lower, banner, note);
  return page;
}
