/** Interactive positioning board, trait tracker, and local saved teams. */
import { el, button, picture, gold, icon, toast, emptyState } from "./dom.js";
function actionDialog(title, copy, confirmText, action, inputValue = null) {
  const dialog = el("dialog", "action-dialog");
  dialog.setAttribute("aria-label", title);
  const form = el("form", "detail-body");
  form.append(el("h2", "", title), el("p", "page-description", copy));
  let input;
  if (inputValue !== null) {
    const label = el("label", "form-label", "Team name");
    input = el("input", "team-name-input");
    input.value = inputValue;
    input.required = true;
    input.maxLength = 60;
    input.placeholder = "My wild idea";
    label.append(input);
    form.append(label);
  }
  const actions = el("div", "dialog-actions");
  const submit = button(confirmText, "button primary");
  submit.type = "submit";
  actions.append(
    button("Cancel", "button secondary", () => dialog.close()),
    submit,
  );
  form.append(actions);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (input && !input.value.trim()) {
      input.setCustomValidity("Enter a team name.");
      input.reportValidity();
      return;
    }
    action(input?.value.trim());
    dialog.close();
  });
  input?.addEventListener("input", () => input.setCustomValidity(""));
  dialog.append(form);
  dialog.addEventListener("close", () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
  input?.focus();
}
export function renderBuilder(context) {
  const team = context.team;
  const page = el("div", "builder-page");
  const header = el("div", "page-intro");
  const title = el("div");
  title.append(
    el(
      "p",
      "eyebrow",
      `SET ${context.catalog.metadata.set_number} / YOUR NEXT GREAT IDEA`,
    ),
    el("h1", "", "Make a little magic."),
    el(
      "p",
      "page-description",
      "Add champions. Find your synergies. Make the board your own.",
    ),
  );
  const save = button("Save team", "button primary", () => {
    if (!team.units.length) {
      toast("Add a champion to your board first.");
      return;
    }
    actionDialog(
      "Give your idea a name.",
      "Save this team on your device. Reusing a name replaces that saved team.",
      "Save team",
      (name) => {
        toast(
          team.save(name)
            ? "Team saved on this device."
            : "Your browser could not save the team.",
        );
        renderSaved();
      },
      "",
    );
  });
  save.prepend(icon("save"));
  header.append(title, save);
  page.append(header);
  const layout = el("div", "builder-layout");
  const arenaPanel = el("section", "arena-panel");
  const arenaHeading = el("div", "arena-heading");
  const count = el("strong");
  const clear = button("Clear board", "text-button", () => {
    if (!team.units.length) return;
    actionDialog(
      "Start with a clear board?",
      "This clears your current board. Your saved teams stay available.",
      "Clear board",
      () => {
        team.clear();
        renderBoard();
      },
    );
  });
  arenaHeading.append(count, clear);
  const arena = el("div", "arena");
  const facing = el("div", "arena-facing", "FRONTLINE");
  const board = el("div", "hex-board");
  board.setAttribute("aria-label", "Team board, 4 rows and 7 columns");
  arena.append(facing, board, el("div", "arena-facing backline", "BACKLINE"));
  const selection = el("div", "board-selection");
  const guidance = el(
    "p",
    "board-guidance",
    "Click a champion below to add. Select a unit, then another hex to move or swap. Drag also works.",
  );
  arenaPanel.append(arenaHeading, arena, selection, guidance);
  const traitPanel = el("aside", "synergy-panel");
  traitPanel.setAttribute("aria-label", "Team synergies");
  const traitHeading = el("div", "synergy-heading");
  traitHeading.append(el("h2", "", "Team synergies"), icon("traits"));
  const traitList = el("div", "synergy-list");
  traitPanel.append(
    traitHeading,
    el(
      "p",
      "synergy-note",
      "Unique champions count once. Avatar doubles its chosen trait. Elder Dragon uses 2 team slots and counts as 2 Riftbeasts.",
    ),
    traitList,
  );
  layout.append(arenaPanel, traitPanel);
  page.append(layout);
  const saveSection = el("section", "saved-section");
  page.append(saveSection);
  const roster = el("section", "builder-roster");
  const rosterHead = el("div", "section-heading");
  rosterHead.append(el("h2", "", "Choose your champions"));
  const search = el("input", "roster-search");
  search.type = "search";
  search.placeholder = "Search champions or traits…";
  search.setAttribute("aria-label", "Search team builder champions");
  const filter = el("select", "select");
  filter.setAttribute("aria-label", "Filter champions by cost");
  filter.append(new Option("All costs", ""));
  for (let cost = 1; cost <= 5; cost++)
    filter.append(new Option(`${cost} gold`, String(cost)));
  const controls = el("div", "roster-controls");
  controls.append(search, filter);
  rosterHead.append(controls);
  const rosterGrid = el("div", "roster-grid");
  roster.append(rosterHead, rosterGrid);
  page.append(roster);
  function renderBoard() {
    const focusedIndex = document.activeElement?.closest(".hex")?.dataset.index;
    const units = team.units;
    count.replaceChildren(
      el(
        "span",
        "",
        `${units.length} champion${units.length === 1 ? "" : "s"} · ${team.teamSlots} slot${team.teamSlots === 1 ? "" : "s"}`,
      ),
      el(
        "span",
        "board-gold",
        `${units.reduce((sum, unit) => sum + unit.cost, 0)} gold`,
      ),
    );
    board.replaceChildren();
    for (let row = 0; row < 4; row++) {
      const rowNode = el("div", "hex-row");
      for (let column = 0; column < 7; column++) {
        const index = row * 7 + column;
        const champion = team.champions.get(team.board[index]);
        const hex = button(
          "",
          `hex${champion ? " occupied" : ""}${team.selected === index ? " selected" : ""}`,
          () => {
            if (team.selected !== null && team.selected !== index) {
              team.move(team.selected, index);
              team.selected = null;
            } else
              team.selected =
                champion && team.selected !== index ? index : null;
            renderBoard();
          },
        );
        hex.setAttribute(
          "aria-label",
          champion
            ? `${champion.name}, row ${row + 1}, column ${column + 1}. Select to move.`
            : `Empty hex, row ${row + 1}, column ${column + 1}`,
        );
        hex.setAttribute("aria-pressed", String(team.selected === index));
        hex.dataset.index = index;
        if (champion) {
          hex.classList.add(`hex-cost-${Math.min(champion.cost, 5)}`);
          hex.draggable = true;
          hex.append(
            picture(
              champion.square_icon_url || champion.icon_url,
              champion.name,
              "hex-portrait",
            ),
            el("span", "hex-name", champion.name),
          );
          hex.addEventListener("dragstart", (event) =>
            event.dataTransfer.setData(
              "application/x-tft-board",
              String(index),
            ),
          );
        } else hex.append(el("span", "hex-plus", "+"));
        hex.addEventListener("dragover", (event) => {
          event.preventDefault();
          hex.classList.add("drag-over");
        });
        hex.addEventListener("dragleave", () =>
          hex.classList.remove("drag-over"),
        );
        hex.addEventListener("drop", (event) => {
          event.preventDefault();
          const source = event.dataTransfer.getData("application/x-tft-board");
          const championId = event.dataTransfer.getData(
            "application/x-tft-champion",
          );
          if (source !== "" && /^\d+$/.test(source) && Number(source) < 28)
            team.move(Number(source), index);
          else if (championId && !team.add(championId, index))
            toast(team.lastError);
          team.selected = null;
          renderBoard();
        });
        rowNode.append(hex);
      }
      board.append(rowNode);
    }
    selection.replaceChildren();
    if (team.selected !== null && team.board[team.selected]) {
      const unit = team.champions.get(team.board[team.selected]);
      selection.append(
        el("span", "", `${unit.name} selected`),
        button("View details", "text-button", () =>
          context.detail("champions", unit),
        ),
        button("Remove", "text-button danger-text", () => {
          team.remove(team.selected);
          team.selected = null;
          renderBoard();
        }),
      );
    } else
      selection.append(
        el(
          "span",
          "muted",
          units.length
            ? "Select a champion to move or remove it."
            : "Your next great team starts here.",
        ),
      );
    traitList.replaceChildren();
    for (const trait of team.traits) {
      const row = button(
        "",
        `synergy-row${trait.active ? " active" : ""}`,
        () => trait.api_name && context.detail("traits", trait),
      );
      const info = el("span", "synergy-info");
      info.append(el("strong", "", trait.name));
      const levels = el("span", "synergy-levels");
      trait.thresholds.forEach((value) =>
        levels.append(el("span", trait.count >= value ? "reached" : "", value)),
      );
      info.append(levels);
      row.append(
        picture(trait.icon_url, trait.name, "trait-picture"),
        el("span", "synergy-count", trait.count),
        info,
      );
      traitList.append(row);
    }
    if (!team.traits.length)
      traitList.append(
        emptyState(
          "Room to grow.",
          "Add champions to discover your team’s traits.",
        ),
      );
    if (focusedIndex !== undefined)
      board
        .querySelector(`[data-index="${focusedIndex}"]`)
        ?.focus({ preventScroll: true });
  }
  function renderSaved() {
    saveSection.replaceChildren();
    if (!team.saved.length) return;
    saveSection.append(el("h2", "", "Saved on this device"));
    const list = el("div", "saved-team-list");
    team.saved.forEach((saved, index) => {
      const savedCount = team.validate(saved.board).filter(Boolean).length;
      const card = el("div", "saved-team");
      const load = button("", "saved-team-load", () =>
        actionDialog(
          `Load “${saved.name}”?`,
          "This replaces your current board with your saved team.",
          "Load team",
          () => {
            team.load(index);
            renderBoard();
            toast("Team loaded.");
          },
        ),
      );
      load.append(
        el("strong", "", saved.name),
        el("small", "", `${savedCount} champion${savedCount === 1 ? "" : "s"}`),
      );
      const remove = button("×", "icon-button", () =>
        actionDialog(
          `Delete “${saved.name}”?`,
          "This removes the saved team from this device.",
          "Delete team",
          () => {
            toast(
              team.deleteSaved(index)
                ? "Saved team deleted."
                : "Could not update local storage.",
            );
            renderSaved();
          },
        ),
      );
      remove.setAttribute("aria-label", `Delete saved team ${saved.name}`);
      card.append(load, remove);
      list.append(card);
    });
    saveSection.append(list);
  }
  function renderRoster() {
    const query = search.value.toLowerCase().trim();
    const champions = context.catalog.champions
      .filter(
        (champion) =>
          `${champion.name} ${champion.traits.join(" ")}`
            .toLowerCase()
            .includes(query) &&
          (!filter.value || champion.cost === Number(filter.value)),
      )
      .sort((a, b) => a.cost - b.cost || a.name.localeCompare(b.name));
    rosterGrid.replaceChildren();
    for (const champion of champions) {
      const pick = button(
        "",
        `roster-unit cost-border-${Math.min(champion.cost, 5)}`,
        () => {
          if (!team.add(champion.api_name)) toast(team.lastError);
          else {
            renderBoard();
            toast(`${champion.name} added to your team.`);
          }
        },
      );
      pick.title = `Add ${champion.name} · ${champion.traits.join(", ")}`;
      pick.draggable = true;
      pick.setAttribute(
        "aria-label",
        `Add ${champion.name}, ${champion.cost} gold`,
      );
      pick.addEventListener("dragstart", (event) =>
        event.dataTransfer.setData(
          "application/x-tft-champion",
          champion.api_name,
        ),
      );
      pick.append(
        picture(
          champion.square_icon_url || champion.icon_url,
          champion.name,
          "roster-portrait",
        ),
        el("strong", "", champion.name),
        gold(champion.cost),
      );
      rosterGrid.append(pick);
    }
    if (!champions.length)
      rosterGrid.append(
        emptyState("No champions found.", "Try another name or trait."),
      );
  }
  search.addEventListener("input", renderRoster);
  filter.addEventListener("change", renderRoster);
  renderBoard();
  renderSaved();
  renderRoster();
  context.refreshBuilder = renderBoard;
  return page;
}
