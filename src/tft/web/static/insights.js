/** Read-only views of real locally harvested match analytics. */
import { el, button, emptyState } from "./dom.js";

function tableSection(title, copy, rows) {
  const section = el("section", "insight-section");
  section.append(el("h2", "", title), el("p", "page-description", copy));
  if (!rows.length) {
    section.append(
      el(
        "p",
        "insight-empty",
        "No boards meet the sample requirements for this comparison.",
      ),
    );
    return section;
  }
  const wrap = el("div", "insight-table-wrap");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", `${title} data table`);
  const table = el("table", "insight-table");
  const head = el("thead");
  const headings = el("tr");
  const columns = Object.keys(rows[0]);
  for (const column of columns) {
    const cell = el("th", "", column);
    cell.scope = "col";
    headings.append(cell);
  }
  head.append(headings);
  const body = el("tbody");
  for (const row of rows) {
    const line = el("tr");
    for (const column of columns) line.append(el("td", "", row[column] ?? "—"));
    body.append(line);
  }
  table.append(head, body);
  wrap.append(table);
  section.append(wrap);
  return section;
}

export function renderInsights() {
  const page = el("div", "insights-page");
  const header = el("div", "page-intro");
  const intro = el("div");
  intro.append(
    el("p", "eyebrow", "LEARN FROM THE BOARDS"),
    el("h1", "", "A closer look at the game."),
    el(
      "p",
      "page-description",
      "Explore patterns in your locally harvested Challenger and Grandmaster matches.",
    ),
  );
  header.append(intro);
  const content = el("div", "insights-content");
  page.append(header, content);
  let requestNumber = 0;
  let versions = [];

  async function load(version = "") {
    const request = ++requestNumber;
    content.replaceChildren(
      el("p", "data-note", "Reading your match collection…"),
    );
    try {
      const response = await fetch(
        `/api/analysis${version ? `?game_version=${encodeURIComponent(version)}` : ""}`,
      );
      if (!response.ok)
        throw new Error(
          "Your local match data could not be read. Refresh the catalog and check the server log.",
        );
      const data = await response.json();
      if (request !== requestNumber) return;
      if (!version) versions = data.versions;
      content.replaceChildren();
      if (!data.sample_count) {
        const empty = emptyState(
          "Every insight starts with a game.",
          "Your static catalog is ready. Harvest ranked matches with a valid Riot API key to see composition popularity and placement comparisons here.",
        );
        empty.append(
          el(
            "code",
            "insight-command",
            ".venv/bin/python scripts/match_harvester.py",
          ),
        );
        empty.append(
          el(
            "p",
            "data-note",
            "Set RIOT_API_KEY in your private .env file, run the command, then refresh this view.",
          ),
          button("Check for matches", "button secondary", () => load()),
        );
        content.append(empty);
        return;
      }
      const controls = el("div", "insight-controls");
      controls.append(
        el(
          "p",
          "insight-sample",
          `${data.sample_count.toLocaleString()} sampled ranked boards`,
        ),
      );
      const label = el("label", "insight-version", "Game version");
      const select = el("select", "select");
      select.append(new Option("All stored versions", ""));
      versions.forEach((value) => select.append(new Option(value, value)));
      select.value = version;
      select.addEventListener("change", () => load(select.value));
      label.append(select);
      controls.append(label);
      content.append(controls);
      if (data.versions.length > 1)
        content.append(
          el(
            "p",
            "insight-notice",
            "This sample combines game versions. Select a single version for a more consistent comparison.",
          ),
        );
      if (data.versions.some((value) => value.includes("?")))
        content.append(
          el(
            "p",
            "insight-notice",
            "Riot did not report a usable patch version for some matches. Their set and ranked queue are verified, but patch-specific comparisons are unavailable.",
          ),
        );
      content.append(
        tableSection(
          "Composition popularity",
          "C = Challenger; G = Grandmaster. Percentages describe sampled boards from each tier.",
          data.population,
        ),
        tableSection(
          "Composition outcomes",
          "Δ = Challenger minus Grandmaster. Top 4% means a top-four finish. Comparisons require enough games in both tiers.",
          data.behavioral,
        ),
        tableSection(
          "Three-star four- and five-cost boards",
          "Frequency and outcomes of upgraded high-cost units in the stored sample.",
          data.highrolls,
        ),
        el(
          "p",
          "data-note",
          "Final boards show associations, not why players made a decision. Util% records item presence, not combat uptime. Cap counts upgraded five-costs without active trait overlap. BIS% compares items to popular sampled builds, not proven optimal builds. Incomplete stored lobbies can undercount other players’ unit copies. Only verified ranked matches from the catalog’s set are included.",
        ),
      );
    } catch (error) {
      if (request !== requestNumber) return;
      content.replaceChildren(
        emptyState(
          "The collection needs a moment.",
          error.message,
          button("Try again", "button secondary", () => load(version)),
        ),
      );
    }
  }
  load();
  return page;
}
