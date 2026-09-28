/** Board rules and persistence regressions without a browser or DOM library. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { beforeEach, test } from "node:test";

const source = await readFile(
  new URL("../../src/tft/web/static/state.js", import.meta.url),
  "utf8",
);
const { TeamState } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);
const DRAFT_KEY = "tft-tactician:18:board";
const TEAMS_KEY = "tft-tactician:18:teams";

class MemoryStorage {
  values = new Map();
  failWrites = false;
  getItem(key) {
    return this.values.get(key) ?? null;
  }
  setItem(key, value) {
    if (this.failWrites) throw new Error("Storage is unavailable");
    this.values.set(key, String(value));
  }
}

function catalog(setNumber = 18) {
  return {
    metadata: { set_number: setNumber },
    champions: [
      { api_name: "DA_Mage", name: "Mage", traits: ["Blossom", "Invoker"] },
      {
        api_name: "DA_Mage_Alternate",
        name: "Mage (Alternate)",
        traits: ["Blossom", "Invoker"],
      },
      { api_name: "DA_Guard", name: "Guard", traits: ["Blossom"] },
      {
        api_name: "DA_Lux18_Blossom",
        name: "Lux (Blossom)",
        traits: ["Blossom", "Avatar"],
      },
      {
        api_name: "DA_18_ElderDragon",
        name: "Elder Dragon",
        traits: ["Apex Predator", "Riftbeast"],
      },
      {
        api_name: "DA_Cinderling18",
        name: "Cinderling",
        traits: ["Riftbeast"],
      },
    ],
    traits: [
      {
        api_name: "DA_Blossom",
        name: "Blossom",
        effects: [{ minUnits: 2 }, { minUnits: 4 }],
      },
      { api_name: "DA_Invoker", name: "Invoker", effects: [{ minUnits: 2 }] },
      {
        api_name: "DA_18_LuxUniqueTrait",
        name: "Avatar",
        effects: [{ minUnits: 1 }],
      },
      {
        api_name: "DA_18_ApexPredator",
        name: "Apex Predator",
        effects: [{ minUnits: 1 }],
      },
      {
        api_name: "DA_Riftbeast18",
        name: "Riftbeast",
        effects: [{ minUnits: 3 }, { minUnits: 5 }],
      },
    ],
  };
}

beforeEach(() => {
  globalThis.localStorage = new MemoryStorage();
});

test("invalid stored JSON and non-array drafts recover to an empty board", () => {
  for (const invalid of ["{bad json", "null", "{}", "42", '"unit"']) {
    localStorage.setItem(DRAFT_KEY, invalid);
    const state = new TeamState(catalog());
    assert.equal(state.board.length, 28);
    assert.equal(state.units.length, 0);
  }
});

test("restored boards discard unknown champion IDs and extra slots", () => {
  localStorage.setItem(
    DRAFT_KEY,
    JSON.stringify(["DA_Mage", "retired_id", ...Array(40).fill("DA_Guard")]),
  );
  const state = new TeamState(catalog());
  assert.equal(state.board.length, 28);
  assert.equal(state.board[0], "DA_Mage");
  assert.equal(state.board[1], null);
  assert.equal(state.units.length, 27);
});

test("malformed saved teams are ignored and loaded boards are validated", () => {
  localStorage.setItem(
    TEAMS_KEY,
    JSON.stringify([
      null,
      { name: 42, board: [] },
      { name: "Missing board" },
      { name: "Valid", board: ["DA_Mage", "retired_id"] },
    ]),
  );
  const state = new TeamState(catalog());
  assert.equal(state.saved.length, 1);
  state.load(0);
  assert.equal(state.board[0], "DA_Mage");
  assert.equal(state.board[1], null);
  assert.equal(state.board.length, 28);
});

test("duplicate units and alternate forms do not multiply shared traits", () => {
  const state = new TeamState(catalog());
  state.add("DA_Mage");
  state.add("DA_Mage");
  state.add("DA_Mage_Alternate");
  assert.equal(state.traits.find((trait) => trait.name === "Blossom").count, 1);
  state.add("DA_Guard");
  const blossom = state.traits.find((trait) => trait.name === "Blossom");
  assert.equal(blossom.count, 2);
  assert.equal(blossom.active, true);
  assert.equal(state.traits[0].name, "Blossom");
});

test("Set 18 Avatar counts its chosen origin twice and Avatar once", () => {
  const state = new TeamState(catalog());
  state.add("DA_Lux18_Blossom");
  assert.equal(state.traits.find((trait) => trait.name === "Blossom").count, 2);
  assert.equal(
    state.traits.find((trait) => trait.name === "Blossom").active,
    true,
  );
  assert.equal(state.traits.find((trait) => trait.name === "Avatar").count, 1);
  state.add("DA_Lux18_Blossom");
  assert.equal(state.traits.find((trait) => trait.name === "Blossom").count, 2);
});

test("Elder Dragon uses two team slots and contributes two Riftbeasts total", () => {
  const state = new TeamState(catalog());
  assert.equal(state.teamSlots, 0);
  state.add("DA_18_ElderDragon");
  assert.equal(state.units.length, 1);
  assert.equal(state.teamSlots, 2);
  assert.equal(
    state.traits.find((trait) => trait.name === "Riftbeast").count,
    2,
  );
  assert.equal(
    state.traits.find((trait) => trait.name === "Riftbeast").active,
    false,
  );
  assert.equal(
    state.traits.find((trait) => trait.name === "Apex Predator").count,
    1,
  );
  state.add("DA_Cinderling18");
  assert.equal(state.units.length, 2);
  assert.equal(state.teamSlots, 3);
  assert.equal(
    state.traits.find((trait) => trait.name === "Riftbeast").count,
    3,
  );
  assert.equal(
    state.traits.find((trait) => trait.name === "Riftbeast").active,
    true,
  );
  assert.equal(new TeamState(catalog()).teamSlots, 3);
});

test("duplicate Elder Dragons consume slots without multiplying trait contributions", () => {
  const state = new TeamState(catalog());
  state.add("DA_18_ElderDragon");
  state.add("DA_18_ElderDragon");
  state.add("DA_Mage");
  assert.equal(state.units.length, 3);
  assert.equal(state.teamSlots, 5);
  assert.equal(
    state.traits.find((trait) => trait.name === "Riftbeast").count,
    2,
  );
  assert.equal(
    state.traits.find((trait) => trait.name === "Apex Predator").count,
    1,
  );
  state.remove(0);
  assert.equal(state.teamSlots, 3);
  state.clear();
  assert.equal(state.teamSlots, 0);
});

test("adding, swapping, removing, and clearing retain a fixed-size persisted board", () => {
  const state = new TeamState(catalog());
  assert.equal(state.add("unknown"), false);
  state.add("DA_Mage", 0);
  state.add("DA_Guard", 1);
  state.move(0, 1);
  assert.deepEqual(state.board.slice(0, 2), ["DA_Guard", "DA_Mage"]);
  state.move(1, 7);
  assert.equal(state.board[1], null);
  assert.equal(state.board[7], "DA_Mage");
  state.remove(0);
  assert.equal(state.units.length, 1);
  assert.deepEqual(new TeamState(catalog()).board, state.board);
  state.clear();
  assert.equal(state.units.length, 0);
  assert.equal(state.board.length, 28);
  assert.equal(new TeamState(catalog()).units.length, 0);
});

test("a full board rejects another unit without replacing an existing slot", () => {
  const state = new TeamState(catalog());
  for (let i = 0; i < 28; i++) assert.equal(state.add("DA_Mage"), true);
  assert.equal(state.add("DA_Guard"), false);
  assert.equal(state.units.length, 28);
  assert.equal(state.board.includes("DA_Guard"), false);
});

test("saving stores independent snapshots and replaces matching names", () => {
  const state = new TeamState(catalog());
  state.add("DA_Mage");
  assert.equal(state.save("  My team  "), true);
  state.add("DA_Guard");
  assert.equal(state.saved[0].board[1], null);
  assert.equal(state.save("My team"), true);
  assert.equal(state.saved.length, 1);
  state.clear();
  state.load(0);
  assert.deepEqual(state.board.slice(0, 2), ["DA_Mage", "DA_Guard"]);
  assert.equal(new TeamState(catalog()).saved[0].name, "My team");
  assert.equal(state.deleteSaved(0), true);
  assert.equal(new TeamState(catalog()).saved.length, 0);
});

test("storage failures leave saved teams intact and report failure", () => {
  const state = new TeamState(catalog());
  state.save("Existing");
  localStorage.failWrites = true;
  assert.equal(state.persist(), false);
  assert.equal(state.save("New"), false);
  assert.equal(state.deleteSaved(0), false);
  assert.deepEqual(
    state.saved.map((team) => team.name),
    ["Existing"],
  );
});

test("drafts and saved teams are isolated between catalog sets", () => {
  const current = new TeamState(catalog(18));
  current.add("DA_Mage");
  current.save("Wilds");
  const previous = new TeamState(catalog(17));
  assert.equal(previous.units.length, 0);
  assert.equal(previous.saved.length, 0);
  previous.add("DA_Guard");
  previous.save("Previous");
  const restored = new TeamState(catalog(18));
  assert.equal(restored.board[0], "DA_Mage");
  assert.deepEqual(
    restored.saved.map((team) => team.name),
    ["Wilds"],
  );
});

test("conflicting Avatar forms cannot make synergy depend on board position", () => {
  const data = catalog();
  data.champions.push({
    api_name: "DA_Lux_Blackthorn",
    name: "Lux (Blackthorn)",
    traits: ["Blackthorn", "Avatar"],
  });
  const state = new TeamState(data);
  assert.equal(state.add("DA_Lux18_Blossom"), true);
  assert.equal(state.add("DA_Lux_Blackthorn"), false);
  assert.match(state.lastError, /Choose one Lux form/);
  const traits = state.traits;
  state.move(0, 27);
  assert.deepEqual(state.traits, traits);
  const restored = state.validate(["DA_Lux18_Blossom", "DA_Lux_Blackthorn"]);
  assert.equal(restored[1], null);
});
