/** Remember which official notes the browser has already shown. */
export const SEEN_KEY = "tft.news.seen";

export function readSeen(storage) {
  try {
    const parsed = JSON.parse(storage.getItem(SEEN_KEY) || "{}");
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return Object.fromEntries(
      Object.entries(parsed).filter(
        ([id, revision]) => typeof id === "string" && typeof revision === "string",
      ),
    );
  } catch {
    return {};
  }
}

export function writeSeen(storage, seen) {
  try {
    storage.setItem(SEEN_KEY, JSON.stringify(seen));
  } catch {
    return false;
  }
  return true;
}

export function markSeen(storage, articles) {
  const seen = readSeen(storage);
  for (const article of articles) {
    if (article?.content_id && article.revision) seen[article.content_id] = article.revision;
  }
  writeSeen(storage, seen);
  return seen;
}

export function articleStatus(article, seen) {
  const previous = seen[article.content_id];
  if (!previous) return "new";
  if (previous !== article.revision) return "updated";
  return "";
}

export function newsBadge(articles, seen) {
  let hasNew = false;
  let hasUpdated = false;
  for (const article of articles) {
    const status = articleStatus(article, seen);
    if (status === "new") hasNew = true;
    if (status === "updated") hasUpdated = true;
  }
  if (hasNew) return "NEW";
  if (hasUpdated) return "UPDATE";
  return "";
}

export function latestOfficialNotes(articles) {
  return articles.find((article) => article.kind === "patch_notes") || articles[0] || null;
}
