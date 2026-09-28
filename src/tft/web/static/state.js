/** Local team persistence and board rules, separate from rendering. */
const BOARD_SIZE = 28;
function readStored(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
}
export class TeamState {
  constructor(catalog) {
    this.catalog = catalog;
    const setNumber = catalog.metadata?.set_number || 18;
    this.draftKey = `tft-tactician:${setNumber}:board`;
    this.teamsKey = `tft-tactician:${setNumber}:teams`;
    this.champions = new Map(
      catalog.champions.map((champion) => [champion.api_name, champion]),
    );
    this.board = this.validate(readStored(this.draftKey, []));
    this.saved = readStored(this.teamsKey, []);
    if (!Array.isArray(this.saved)) this.saved = [];
    this.saved = this.saved.filter(
      (team) => typeof team?.name === "string" && Array.isArray(team?.board),
    );
    this.selected = null;
  }
  validate(board) {
    let avatarId;
    return Array.from({ length: BOARD_SIZE }, (_, i) => {
      const id =
        Array.isArray(board) && this.champions.has(board[i]) ? board[i] : null;
      if (this.champions.get(id)?.traits.includes("Avatar")) {
        if (avatarId && avatarId !== id) return null;
        avatarId = id;
      }
      return id;
    });
  }
  persist() {
    try {
      localStorage.setItem(this.draftKey, JSON.stringify(this.board));
      return true;
    } catch {
      return false;
    }
  }
  add(id, index = this.board.indexOf(null)) {
    this.lastError = "";
    if (
      !this.champions.has(id) ||
      !Number.isInteger(index) ||
      index < 0 ||
      index >= BOARD_SIZE
    ) {
      this.lastError = "Your board is full. Remove a champion to make room.";
      return false;
    }
    if (
      this.champions.get(id).traits.includes("Avatar") &&
      this.board.some(
        (existing, slot) =>
          slot !== index &&
          existing !== id &&
          this.champions.get(existing)?.traits.includes("Avatar"),
      )
    ) {
      this.lastError =
        "Choose one Lux form for your team. Remove the current form before adding another.";
      return false;
    }
    this.board[index] = id;
    this.persist();
    return true;
  }
  remove(index) {
    if (!Number.isInteger(index) || index < 0 || index >= BOARD_SIZE) return;
    this.board[index] = null;
    this.persist();
  }
  move(from, to) {
    if (
      ![from, to].every(
        (index) => Number.isInteger(index) && index >= 0 && index < BOARD_SIZE,
      )
    )
      return;
    [this.board[from], this.board[to]] = [this.board[to], this.board[from]];
    this.persist();
  }
  clear() {
    this.board.fill(null);
    this.selected = null;
    this.persist();
  }
  save(name) {
    const team = {
      name: name.trim().slice(0, 60),
      board: [...this.board],
      savedAt: new Date().toISOString(),
    };
    const next = [
      team,
      ...this.saved.filter((saved) => saved.name !== team.name),
    ].slice(0, 30);
    try {
      localStorage.setItem(this.teamsKey, JSON.stringify(next));
      this.saved = next;
      return true;
    } catch {
      return false;
    }
  }
  load(index) {
    this.board = this.validate(this.saved[index]?.board);
    this.selected = null;
    this.persist();
  }
  deleteSaved(index) {
    const next = this.saved.filter((_, i) => i !== index);
    try {
      localStorage.setItem(this.teamsKey, JSON.stringify(next));
      this.saved = next;
      return true;
    } catch {
      return false;
    }
  }
  get units() {
    return this.board.filter(Boolean).map((id) => this.champions.get(id));
  }
  get teamSlots() {
    // Apex Predator consumes two team slots even though it occupies one hex.
    return this.units.reduce(
      (slots, unit) => slots + (unit.traits.includes("Apex Predator") ? 2 : 1),
      0,
    );
  }
  get traits() {
    const counts = new Map();
    // Alternate forms of the same champion must not multiply trait contributions.
    const units = new Map(
      this.units.map((unit) => [unit.name.replace(/\s*\([^)]*\)$/, ""), unit]),
    );
    for (const unit of units.values())
      for (const name of unit.traits) {
        // Riot's Enchanted Wilds overview confirms Elder Dragon counts as two Riftbeasts.
        const doubled =
          (unit.traits.includes("Avatar") && name !== "Avatar") ||
          (unit.traits.includes("Apex Predator") && name === "Riftbeast");
        const contribution = doubled ? 2 : 1;
        counts.set(name, (counts.get(name) || 0) + contribution);
      }
    return [...counts]
      .map(([name, count]) => {
        const trait = this.catalog.traits.find((entry) => entry.name === name);
        const thresholds = (trait?.effects || [])
          .map((effect) => effect.minUnits)
          .filter((value) => value > 0)
          .sort((a, b) => a - b);
        return {
          ...trait,
          name,
          count,
          thresholds,
          active: thresholds.some((value) => count >= value),
        };
      })
      .sort(
        (a, b) =>
          Number(b.active) - Number(a.active) ||
          b.count - a.count ||
          a.name.localeCompare(b.name),
      );
  }
}
