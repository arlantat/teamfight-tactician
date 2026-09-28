/** CDragon tooltip formatting stays useful without evaluating source markup. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const source = await readFile(
  new URL("../../src/tft/web/static/dom.js", import.meta.url),
  "utf8",
);
const { description } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);

test("plain descriptions preserve text and omit optional empty values", () => {
  assert.equal(
    description("Deal damage to the target."),
    "Deal damage to the target.",
  );
  assert.equal(description(), "");
  assert.equal(description("  Gain  Health.  "), "Gain Health.");
});

test("tooltip tags, icon tokens, and localization markers are removed", () => {
  const value =
    "<attention>Gain power.</attention><br />Then heal.&nbsp;&amp; shield. %i:scaleAP% {{SpellName}}";
  assert.equal(description(value), "Gain power.\nThen heal. & shield.");
});

test("numeric effect names are matched without case sensitivity", () => {
  const value = "Gain @Health@ Health and @attackdamage@ Attack Damage.";
  assert.equal(
    description(value, { health: 150, AttackDamage: 25 }),
    "Gain 150 Health and 25 Attack Damage.",
  );
  assert.equal(description("Gain @ZERO@ armor.", { Zero: 0 }), "Gain 0 armor.");
});

test("a known effect supports numeric multipliers and readable rounding", () => {
  assert.equal(
    description("Gain @DamageAmp*100@% damage.", { DamageAmp: 0.125 }),
    "Gain 12.5% damage.",
  );
  assert.equal(
    description("Heal @Healing*2@.", { Healing: 12.345 }),
    "Heal 24.69.",
  );
});

test("unresolved effects and unsupported expressions use an honest placeholder", () => {
  assert.equal(description("Deal @Missing@ damage."), "Deal ◇ damage.");
  assert.equal(
    description("@Damage@ @Damage*bad@ @Damage*2*3@", { Damage: "20" }),
    "◇ ◇ ◇",
  );
  assert.equal(description("@Damage*bad@ @Damage*2*3@", { Damage: 20 }), "◇ ◇");
  assert.equal(description("@Damage@", null), "◇");
});

test("escaped source remains text and effect expressions are never executed", () => {
  globalThis.tooltipExecuted = false;
  try {
    const value =
      '&lt;img src=x onerror="globalThis.tooltipExecuted=true"&gt; @Damage*(globalThis.tooltipExecuted=true)@';
    assert.equal(
      description(value, { Damage: 20 }),
      '<img src=x onerror="globalThis.tooltipExecuted=true"> ◇',
    );
    assert.equal(globalThis.tooltipExecuted, false);
  } finally {
    delete globalThis.tooltipExecuted;
  }
});
