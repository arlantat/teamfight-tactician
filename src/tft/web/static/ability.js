/** Interactive champion ability descriptions with transparent data provenance. */
import { el, button, picture } from "./dom.js";
import { formatAbilityText } from "./ability-format.js";

function sourceDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "date unavailable" : date.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

function sourceLink(text, url) {
  const node = el("a", "text-link", text);
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return el("span", "", text);
    node.href = parsed.href;
    node.target = "_blank";
    node.rel = "noopener noreferrer";
    return node;
  } catch {
    return el("span", "", text);
  }
}

function provenance(source = {}) {
  const box = el("details", "ability-provenance");
  box.append(el("summary", "", `${source.name || "Ability"} reference · ${sourceDate(source.generated)}`));
  const patch = source.patch || "unknown";
  const verified = source.verified_patch;
  box.append(el("p", "", `Source labelled ${patch.toUpperCase()}. ${verified ? `Listed hotfix changes checked against Riot ${verified}; ` : ""}full live parity unverified.`));
  if (source.verification_note) box.append(el("p", "", source.verification_note));
  const links = el("div", "ability-source-links");
  if (source.url) links.append(sourceLink("Reference data ↗", source.url));
  if (source.patch_notes_url) links.append(sourceLink(`Riot ${verified || "patch"} notes ↗`, source.patch_notes_url));
  box.append(links);
  if (source.corrections?.length) {
    const corrections = el("ul");
    for (const correction of source.corrections) {
      const text = typeof correction === "string" ? correction : correction.note || correction.description || `${correction.row || "Ability value"} updated from Riot patch notes.`;
      corrections.append(el("li", "", text));
    }
    box.append(corrections);
  }
  return box;
}

function footerDetails(form, star) {
  const rows = (form.footer || []).filter((row) => row.show !== false && row.desc);
  if (!rows.length) return null;
  const disclosure = el("details", "source-values ability-breakdown");
  disclosure.append(el("summary", "", `Ability breakdown · ${star}★`));
  const values = el("div", "ability-footer");
  for (const row of rows) {
    const curves = { ...form.curve_values, ...row.curveValues };
    if (row.row && Array.isArray(row.values)) curves[row.row] = row.values;
    values.append(el("p", "", formatAbilityText(row.desc, { ...form, curve_values: curves }, star)));
  }
  disclosure.append(values);
  return disclosure;
}

/** Return a complete ability section for an enriched catalog champion. */
export function renderAbilityDetails(item) {
  const detail = item.ability_detail;
  const forms = detail?.forms || [];
  const section = el("section", "champion-ability");
  section.setAttribute("aria-label", `${item.name} ability`);
  if (!forms.length) return section;
  let formIndex = 0;
  let star = 1;
  const heading = el("div", "ability-heading");
  if (/^https:\/\//i.test(item.ability_icon_url || ""))
    heading.append(picture(item.ability_icon_url, item.ability_name, "item-picture"));
  const title = el("h3", "");
  heading.append(title);
  const controls = el("div", "ability-controls");
  if (forms.length > 1) {
    const label = el("label", "ability-form-label", "Ability form");
    const select = el("select", "ability-form-select");
    select.setAttribute("aria-label", "Ability form");
    forms.forEach((form, index) => {
      const option = el("option", "", form.label || form.name || `Form ${index + 1}`);
      option.value = String(index);
      select.append(option);
    });
    select.addEventListener("change", () => { formIndex = Number(select.value); update(); });
    label.append(select);
    controls.append(label);
  }
  const stars = el("div", "ability-star-selector");
  stars.setAttribute("role", "group");
  stars.setAttribute("aria-label", "Ability star level");
  for (let level = 1; level <= 4; level++) {
    const choice = button(`${level}★`, "ability-star", () => { star = level; update(); });
    choice.setAttribute("aria-label", `${level} star ability`);
    choice.dataset.star = String(level);
    stars.append(choice);
  }
  controls.append(stars);
  const content = el("div", "ability-resolved-text");
  content.setAttribute("aria-live", "polite");
  const caveat = el("p", "ability-source-caption", `${detail.source?.name || "Ability"} reference · ${sourceDate(detail.source?.generated)} · source ${String(detail.source?.patch || "unknown").toUpperCase()}. Full live parity unverified.`);
  section.append(heading, controls, content, el("p", "calculation-note", "AD / AP indicate scaling. Health and combat-dependent effects stay as formulas; “variable” needs in-game state."), caveat, provenance(detail.source));
  function update() {
    const form = forms[formIndex];
    title.textContent = form.name || item.ability_name || "Ability";
    for (const choice of stars.children) {
      const selected = Number(choice.dataset.star) === star;
      choice.classList.toggle("active", selected);
      choice.setAttribute("aria-pressed", String(selected));
    }
    const description = el("p", "", formatAbilityText(form.description, form, star));
    content.replaceChildren(description);
    const footer = footerDetails(form, star);
    if (footer) content.append(footer);
  }
  update();
  return section;
}
