/** Application bootstrap, route coordination, and catalog-wide search. */
import {
  el,
  button,
  icon,
  picture,
  toast,
  emptyState,
  humanize,
} from "./dom.js";
import { TeamState } from "./state.js";
import { renderOverview } from "./overview.js";
import { renderCatalog, displayEntries } from "./catalog.js";
import { renderBuilder } from "./builder.js";
import { showDetail } from "./details.js";
import { renderInsights } from "./insights.js";
import { renderExplorer } from "./explorer.js";
import { renderNotes, renderNewsPreview } from "./notes.js";
import { latestOfficialNotes, newsBadge, readSeen } from "./news-state.js";
const ROUTES = [
  "overview",
  "notes",
  "champions",
  "traits",
  "items",
  "augments",
  "builder",
  "insights",
  "explorer",
];
const LABELS = {
  overview: "Overview",
  notes: "Patch notes",
  champions: "Champions",
  traits: "Traits",
  items: "Items",
  augments: "Augments",
  builder: "Team Builder",
  insights: "Insights",
  explorer: "Explorer",
};
const main = document.querySelector("#main");
let context;
function setupNavigation() {
  const navigation = document.querySelector("#navigation");
  for (const route of ROUTES) {
    const item = el("a", "nav-item");
    item.href = `#${route}`;
    item.dataset.route = route;
    item.append(icon(route), el("span", "", LABELS[route]));
    if (route === "builder") item.append(el("small", "nav-new", "CREATE"));
    navigation.append(item);
  }
}
function activeRoute() {
  const requested = location.hash.slice(1).split("?")[0];
  return ROUTES.includes(requested) ? requested : "overview";
}
function updateNewsChrome() {
  const nav = document.querySelector('[data-route="notes"]');
  nav?.querySelector(".nav-new")?.remove();
  const articles = context?.news?.articles || [];
  const badge = newsBadge(articles, readSeen(localStorage));
  if (nav && badge) nav.append(el("small", "nav-new", badge));
  const official = document.querySelector("#official-notes-link");
  const latest = latestOfficialNotes(articles);
  if (official && latest?.url) official.href = latest.url;
  const preview = document.querySelector("#notes-preview");
  if (preview && context?.news) preview.replaceWith(renderNewsPreview(context.news));
}
function navigate() {
  document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
  const route = activeRoute();
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.route === route);
    if (item.dataset.route === route) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  document.querySelector("#route-label").textContent = LABELS[route];
  document.title = `${LABELS[route]} · Teamfight Tactician`;
  if (!context) return;
  context.refreshBuilder = null;
  main.replaceChildren(
    route === "overview"
      ? renderOverview(context.catalog, context)
      : route === "notes"
        ? renderNotes(context.news, context.newsFailed, loadNews)
        : route === "builder"
          ? renderBuilder(context)
          : route === "insights"
            ? renderInsights()
            : route === "explorer"
              ? renderExplorer(context)
              : renderCatalog(route, context),
  );
  updateNewsChrome();
  window.scrollTo({ top: 0, behavior: "instant" });
}
function setupDialogs() {
  const detail = document.querySelector("#detail-dialog");
  detail
    .querySelector(".dialog-close")
    .addEventListener("click", () => detail.close());
  for (const dialog of document.querySelectorAll("dialog"))
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (
        event.clientX < bounds.left ||
        event.clientX > bounds.right ||
        event.clientY < bounds.top ||
        event.clientY > bounds.bottom
      )
        dialog.close();
    });
  const search = document.querySelector("#search-dialog");
  const input = document.querySelector("#command-input");
  search
    .querySelector(".icon-button")
    .addEventListener("click", () => search.close());
  const openSearch = () => {
    search.showModal();
    input.value = "";
    renderSearch("");
    input.focus();
  };
  document
    .querySelector("#global-search")
    .addEventListener("click", openSearch);
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      search.open ? search.close() : openSearch();
    }
  });
  input.addEventListener("input", () => renderSearch(input.value));
}
function renderSearch(query) {
  const results = document.querySelector("#command-results");
  results.replaceChildren();
  if (!context) {
    results.append(
      emptyState("Catalog is loading.", "Search will be ready in a moment."),
    );
    return;
  }
  if (!query.trim()) {
    results.append(
      el(
        "p",
        "command-hint",
        "Search every champion, trait, item and augment in one place.",
      ),
    );
    return;
  }
  const term = query.toLowerCase().trim();
  let count = 0;
  for (const kind of ["champions", "traits", "items", "augments"]) {
    const matches = displayEntries(kind, context.catalog[kind])
      .filter((item) => item.name.toLowerCase().includes(term))
      .slice(0, 6);
    if (!matches.length) continue;
    results.append(el("p", "command-category", kind.toUpperCase()));
    for (const item of matches) {
      const row = button("", "command-result", () => {
        document.querySelector("#search-dialog").close();
        context.detail(kind, item);
      });
      row.append(
        picture(
          item.square_icon_url || item.icon_url,
          item.name,
          "command-picture",
        ),
        el("strong", "", item.name),
        el(
          "small",
          "",
          item.cost
            ? `${item.cost} gold`
            : humanize(item.category || item.tier || "Trait"),
        ),
      );
      results.append(row);
      count++;
    }
  }
  if (!count)
    results.append(emptyState("Nothing found.", "Try a different name."));
}
async function loadNews() {
  if (!context) return;
  try {
    const response = await fetch("/api/news", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("news");
    const news = await response.json();
    if (!news || !Array.isArray(news.articles)) throw new Error("news");
    context.news = news;
    context.newsFailed = false;
  } catch {
    context.newsFailed = true;
  }
  if (activeRoute() === "notes") navigate();
  else updateNewsChrome();
}
async function boot() {
  try {
    const response = await fetch("/api/catalog", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(
        typeof error.detail === "string"
          ? error.detail
          : `Catalog request failed (${response.status}).`,
      );
    }
    const catalog = await response.json();
    if (
      !catalog.metadata ||
      !["champions", "traits", "items", "augments"].every((key) =>
        Array.isArray(catalog[key]),
      )
    )
      throw new Error("The catalog response is incomplete.");
    const team = new TeamState(catalog);
    context = {
      catalog,
      team,
      news: null,
      newsFailed: false,
      detail: (kind, item) => showDetail(kind, item, context),
      add: (champion) => {
        if (!team.add(champion.api_name)) {
          toast(team.lastError);
          return;
        }
        toast(`${champion.name} added to your team.`);
        context.refreshBuilder?.();
      },
    };
    document.querySelector("#patch-label").textContent = catalog.metadata.patch
      ? `PATCH ${catalog.metadata.patch}`
      : `SET ${catalog.metadata.set_number}`;
    document.querySelector(".set-emblem").textContent =
      catalog.metadata.set_number;
    document.querySelector(".set-switch strong").textContent =
      catalog.metadata.set_name;
    navigate();
    loadNews();
  } catch (error) {
    main.replaceChildren(
      emptyState(
        "The field guide is taking a moment.",
        error.message,
        button("Try again", "button primary", boot),
      ),
    );
  }
}
setupNavigation();
setupDialogs();
window.addEventListener("hashchange", navigate);
boot();
