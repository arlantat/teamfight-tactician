/** Official patch notes: Riot titles, teasers, and heading outlines. */
import { el, link, icon, picture, emptyState, sectionHeading, button } from "./dom.js";
import {
  articleStatus,
  latestOfficialNotes,
  markSeen,
  readSeen,
} from "./news-state.js";

function officialLink(href, className, text) {
  const node = link(text, href, className);
  node.target = "_blank";
  node.rel = "noopener noreferrer";
  return node;
}

function statusChip(article, seen) {
  const status = articleStatus(article, seen);
  if (!status) return null;
  return el("span", `note-chip ${status}`, status === "new" ? "New" : "Updated");
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function headingList(article) {
  const titles = (article.headings || [])
    .filter((heading) => heading.level === 2)
    .map((heading) => heading.text)
    .filter(Boolean)
    .slice(0, 8);
  if (!titles.length) return null;
  const list = el("ul", "note-outline");
  for (const title of titles) list.append(el("li", "", title));
  return list;
}

function articleCard(article, seen) {
  const card = el("article", "note-card");
  const body = el("div", "note-card-body");
  const meta = el("div", "note-meta");
  const kind =
    article.kind === "patch_notes"
      ? article.patch
        ? `Patch ${article.patch}`
        : "Patch notes"
      : article.kind === "rundown"
        ? "Rundown"
        : "Game update";
  meta.append(el("span", "note-kind", kind));
  const published = formatDate(article.published_at);
  if (published) meta.append(el("span", "", published));
  const chip = statusChip(article, seen);
  if (chip) meta.append(chip);
  for (const label of article.mid_patch || [])
    meta.append(el("span", "note-chip mid", label));
  body.append(meta, el("h2", "", article.title));
  if (article.description) body.append(el("p", "", article.description));
  const outline = headingList(article);
  if (outline) body.append(outline);
  const actions = el("div", "note-actions");
  actions.append(officialLink(article.url, "button ghost", "Read on Riot's site"));
  actions.lastChild.append(icon("arrow"));
  body.append(actions);
  if (article.image_url)
    card.append(picture(article.image_url, article.title, "note-picture"));
  card.append(body);
  return card;
}

export function renderNewsPreview(news) {
  const section = el("section", "notes-preview");
  section.id = "notes-preview";
  const latest = latestOfficialNotes(news?.articles || []);
  if (!latest) return section;
  const seen = readSeen(localStorage);
  section.append(
    sectionHeading("OFFICIAL NOTES", latest.title, "#notes", "All notes"),
  );
  const card = el("div", "notes-preview-card");
  const text = el("div");
  const chips = el("div", "note-meta");
  const status = statusChip(latest, seen);
  if (status) chips.append(status);
  if (latest.patch) chips.append(el("span", "note-kind", `Patch ${latest.patch}`));
  for (const label of latest.mid_patch || [])
    chips.append(el("span", "note-chip mid", label));
  if (latest.description) text.append(chips, el("p", "", latest.description));
  else text.append(chips);
  const actions = el("div", "note-actions");
  actions.append(
    officialLink(latest.url, "button ghost", "Riot's notes"),
    link("In the field guide", "#notes", "text-link"),
  );
  actions.lastChild.append(icon("arrow"));
  text.append(actions);
  if (latest.image_url)
    card.append(picture(latest.image_url, latest.title, "note-picture"));
  card.append(text);
  section.append(card);
  return section;
}

export function renderNotes(news, failed = false, retry) {
  const page = el("div", "notes-page");
  const intro = el("div", "page-intro");
  const text = el("div");
  text.append(el("p", "eyebrow", "FROM THE SOURCE"), el("h1", "", "The latest official notes."));
  intro.append(text);
  page.append(intro);
  if (!news && failed) {
    page.append(
      emptyState(
        "Official notes are unavailable.",
        "Try again in a moment.",
        retry ? button("Try again", "button primary", retry) : undefined,
      ),
    );
    return page;
  }
  if (!news) {
    page.append(el("p", "data-note", "Reading official notes…"));
    return page;
  }
  if (!news.articles?.length) {
    page.append(
      emptyState(
        "No official notes yet.",
        "",
        officialLink(
          "https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/",
          "button primary",
          "Open Riot's updates",
        ),
      ),
    );
    return page;
  }
  const seen = readSeen(localStorage);
  const list = el("div", "notes-list");
  for (const article of news.articles) list.append(articleCard(article, seen));
  page.append(list);
  markSeen(localStorage, news.articles);
  return page;
}
