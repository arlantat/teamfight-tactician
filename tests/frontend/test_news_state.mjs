/** Remember which official notes the browser has already shown. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const source = await readFile(
  new URL("../../src/tft/web/static/news-state.js", import.meta.url),
  "utf8",
);
const { articleStatus, latestOfficialNotes, markSeen, newsBadge, readSeen, SEEN_KEY } =
  await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

class MemoryStorage {
  values = new Map();
  getItem(key) {
    return this.values.get(key) ?? null;
  }
  setItem(key, value) {
    this.values.set(key, String(value));
  }
}

function article(id, revision, kind = "patch_notes") {
  return { content_id: id, revision, kind, title: id };
}

test("unseen notes are new and a later CMS revision is an update", () => {
  const seen = { "patch-18-2": "rev-1" };
  assert.equal(articleStatus(article("patch-18-3", "rev-a"), seen), "new");
  assert.equal(articleStatus(article("patch-18-2", "rev-2"), seen), "updated");
  assert.equal(articleStatus(article("patch-18-2", "rev-1"), seen), "");
});

test("the nav badge prefers a new patch over a mid-patch revision", () => {
  const articles = [article("patch-18-2", "rev-2"), article("patch-18-3", "rev-a")];
  const seen = { "patch-18-2": "rev-1" };
  assert.equal(newsBadge(articles, seen), "NEW");
  assert.equal(newsBadge([article("patch-18-2", "rev-2")], seen), "UPDATE");
  assert.equal(newsBadge([article("patch-18-2", "rev-1")], seen), "");
});

test("opening notes records the current revision so mid-patch edits can surface later", () => {
  const storage = new MemoryStorage();
  markSeen(storage, [article("patch-18-2", "rev-1")]);
  assert.equal(JSON.parse(storage.getItem(SEEN_KEY))["patch-18-2"], "rev-1");
  markSeen(storage, [article("patch-18-2", "rev-2")]);
  assert.equal(readSeen(storage)["patch-18-2"], "rev-2");
});

test("the overview card prefers written patch notes over a video rundown", () => {
  const rundown = article("rundown", "r", "rundown");
  const notes = article("patch-18-2", "rev-1");
  assert.equal(latestOfficialNotes([rundown, notes]), notes);
  assert.equal(latestOfficialNotes([rundown]), rundown);
});
