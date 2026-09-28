/** Accessible detail panels with safe game text and original graphics. */
import { renderAbilityDetails } from "./ability.js";
import {
  el,
  button,
  picture,
  gold,
  icon,
  description,
  humanize,
} from "./dom.js";
const STAT_LABELS = {
  hp: "Health",
  damage: "Attack damage",
  armor: "Armor",
  magicResist: "Magic resist",
  attackSpeed: "Attack speed",
  range: "Range",
  initialMana: "Starting mana",
  mana: "Mana",
  critChance: "Critical chance",
  critMultiplier: "Critical damage",
};
function statGrid(values, labels = {}) {
  const grid = el("dl", "stats-grid");
  for (const [key, value] of Object.entries(values || {})) {
    if (value === null || typeof value === "object" || /^\{/.test(key))
      continue;
    const pair = el("div");
    pair.append(
      el("dt", "", labels[key] || humanize(key)),
      el(
        "dd",
        "",
        typeof value === "number" ? Number(value.toFixed(2)) : value,
      ),
    );
    grid.append(pair);
  }
  return grid;
}
function detailText(item, effects = {}) {
  const result = el("div", "detail-description");
  const text = description(item, effects);
  result.append(
    el(
      "p",
      "",
      text || "Additional description is not available in the source data.",
    ),
  );
  if (text.includes("◇"))
    result.append(
      el(
        "p",
        "calculation-note",
        "◇ A value unavailable in this export or dependent on combat. Check the values below where available.",
      ),
    );
  return result;
}
function detailChampion(item, context) {
  const content = el("div");
  content.append(
    picture(
      item.icon_url || item.square_icon_url,
      item.name,
      "detail-splash",
      true,
    ),
  );
  const body = el("div", "detail-body");
  const head = el("div", "detail-title");
  head.append(el("h2", "", item.name), gold(item.cost));
  body.append(el("p", "eyebrow", humanize(item.role || "CHAMPION")), head);
  const traits = el("div", "detail-traits");
  for (const name of item.traits) {
    const trait = context.catalog.traits.find((entry) => entry.name === name);
    const tag = button(
      name,
      "trait-tag",
      () => trait && context.detail("traits", trait),
    );
    if (trait) tag.prepend(picture(trait.icon_url, name, "micro-trait"));
    traits.append(tag);
  }
  body.append(traits);
  if (item.ability_detail?.forms?.length) {
    body.append(renderAbilityDetails(item));
  } else {
    const ability = el("div", "ability-heading");
    ability.append(
      picture(item.ability_icon_url, item.ability_name, "item-picture"),
      el("div", "", item.ability_name || "Ability"),
    );
    body.append(ability, detailText(item.ability_description));
    const variables = (item.ability_variables || []).filter(
      (variable) => variable.name && Array.isArray(variable.value),
    );
    if (variables.length) {
      const disclosure = el("details", "source-values");
      disclosure.append(el("summary", "", "Ability values · 1★ / 2★ / 3★"));
      const values = el("dl", "ability-values");
      for (const variable of variables) {
        const row = el("div");
        row.append(
          el("dt", "", humanize(variable.name)),
          el(
            "dd",
            "",
            variable.value
              .slice(1, 4)
              .map((value) =>
                typeof value === "number" ? Number(value.toFixed(2)) : "—",
              )
              .join(" / "),
          ),
        );
        values.append(row);
      }
      disclosure.append(values);
      body.append(disclosure);
    }
  }
  body.append(
    el("h3", "detail-subheading", "Base stats · 1 star"),
    statGrid(item.stats, STAT_LABELS),
  );
  const add = button(`Add ${item.name} to team`, "button primary wide", () =>
    context.add(item),
  );
  add.prepend(icon("builder"));
  body.append(add);
  content.append(body);
  return content;
}
function detailTrait(item, context) {
  const content = el("div", "detail-body");
  const header = el("div", "large-entity-heading");
  header.append(picture(item.icon_url, item.name, "large-trait"));
  const name = el("div");
  name.append(el("p", "eyebrow", "TRAIT"), el("h2", "", item.name));
  header.append(name);
  content.append(header, detailText(item.description));
  const levels = el("div", "trait-levels");
  for (const effect of item.effects || []) {
    const level = el("div", `trait-level style-${effect.style}`);
    level.append(
      el("strong", "", effect.minUnits),
      el("span", "", `${effect.minUnits} unique champions`),
    );
    levels.append(level);
    if (Object.keys(effect.variables || {}).length) {
      const values = el("details", "source-values");
      values.append(
        el("summary", "", `${effect.minUnits}-unit effect values`),
        statGrid(effect.variables),
      );
      levels.append(values);
    }
  }
  content.append(
    levels,
    el("h3", "detail-subheading", "Champions with this trait"),
  );
  const members = el("div", "detail-member-grid");
  for (const champion of context.catalog.champions.filter((entry) =>
    entry.traits.includes(item.name),
  )) {
    const member = button("", "detail-member", () =>
      context.detail("champions", champion),
    );
    member.append(
      picture(
        champion.square_icon_url || champion.icon_url,
        champion.name,
        "member-portrait",
      ),
      el("strong", "", champion.name),
      gold(champion.cost),
    );
    members.append(member);
  }
  content.append(members);
  return content;
}
function detailItem(kind, item, context) {
  const content = el("div", "detail-body");
  const header = el("div", "large-entity-heading");
  header.append(picture(item.icon_url, item.name, "large-item"));
  const name = el("div");
  name.append(
    el("p", "eyebrow", humanize(item.category || item.tier || kind)),
    el("h2", "", item.name),
  );
  header.append(name);
  content.append(header, detailText(item.description, item.effects));
  if (item.composition?.length) {
    content.append(el("h3", "detail-subheading", "Recipe"));
    const recipe = el("div", "detail-recipe");
    item.composition.forEach((id, index) => {
      const component = context.catalog.items.find(
        (entry) => entry.api_name === id,
      );
      if (index) recipe.append(el("span", "recipe-plus", "+"));
      const node = button(
        "",
        "recipe-component",
        () => component && context.detail("items", component),
      );
      node.append(
        picture(component?.icon_url, component?.name, "item-picture"),
        el(
          "span",
          "",
          component?.name || humanize(id.replace(/^TFT_Item_/, "")),
        ),
      );
      recipe.append(node);
    });
    content.append(recipe);
  }
  const grid = statGrid(item.effects);
  if (grid.childElementCount) {
    const disclosure = el("details", "source-values");
    disclosure.append(el("summary", "", "Effect values from game data"), grid);
    content.append(disclosure);
  }
  if (kind === "items") {
    const builds = context.catalog.items.filter((entry) =>
      entry.composition?.includes(item.api_name),
    );
    if (builds.length) {
      content.append(el("h3", "detail-subheading", "Builds into"));
      const list = el("div", "builds-into");
      for (const build of builds) {
        const node = button("", "recipe-component", () =>
          context.detail("items", build),
        );
        node.append(
          picture(build.icon_url, build.name, "tiny-item"),
          el("span", "", build.name),
        );
        list.append(node);
      }
      content.append(list);
    }
  }
  return content;
}
export function showDetail(kind, item, context) {
  const dialog = document.querySelector("#detail-dialog");
  const content = document.querySelector("#detail-content");
  content.replaceChildren(
    kind === "champions"
      ? detailChampion(item, context)
      : kind === "traits"
        ? detailTrait(item, context)
        : detailItem(kind, item, context),
  );
  dialog.setAttribute("aria-label", item.name);
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop = 0;
  dialog.querySelector(".dialog-close").focus({ preventScroll: true });
}
