// Structural checks for the hand-designed 5x5 mascot sprites (src/sprites.js). These don't touch
// the display or any sim instance — just confirm every grid is well-formed and every character
// resolves to a color, so a typo doesn't silently render as a blank or wrong-colored window.
import { test } from "node:test";
import assert from "node:assert/strict";

import { MASCOTS } from "../src/sprites.js";

const SIZE = 5;

test("every mascot defines a 5x5 sprite", () => {
  for (const [id, m] of Object.entries(MASCOTS)) {
    assert.ok(Array.isArray(m.sprite5), `${id}: sprite5 is missing`);
  }
});

test("every 5x5 sprite is a 5x5 grid of known characters", () => {
  for (const [id, m] of Object.entries(MASCOTS)) {
    assert.equal(m.sprite5.length, SIZE, `${id}: sprite5 must have ${SIZE} rows, has ${m.sprite5.length}`);
    for (const row of m.sprite5) {
      assert.equal(row.length, SIZE, `${id}: sprite5 row "${row}" must be ${SIZE} chars`);
      for (const ch of row) {
        assert.ok(ch === "." || ch === "E" || ch === "M" || ch in m.colors, `${id}: unknown sprite char "${ch}"`);
      }
    }
  }
});

test("every 5x5 sprite has at least one eye and keeps its mouth/beak", () => {
  for (const [id, m] of Object.entries(MASCOTS)) {
    assert.ok(m.sprite5.some((row) => row.includes("E")), `${id}: 5x5 sprite has no eye (E)`);
    assert.ok(m.sprite5.some((row) => row.includes("M")), `${id}: 5x5 sprite has no mouth/beak (M)`);
  }
});

test("5x5 poses (idle/blink/eat/sleep) are derived and stay well-formed", () => {
  for (const [id, m] of Object.entries(MASCOTS)) {
    assert.ok(m.poses5, `${id}: poses5 is missing`);
    assert.deepEqual(Object.keys(m.poses5), ["idle", "blink", "eat", "sleep"], `${id}: unexpected pose set`);
    for (const [pose, rows] of Object.entries(m.poses5)) {
      assert.equal(rows.length, SIZE, `${id} ${pose}: must have ${SIZE} rows`);
      for (const row of rows) assert.equal(row.length, SIZE, `${id} ${pose}: row "${row}" must be ${SIZE} chars`);
    }
    // blink/sleep must actually remove the open eye, and eat must remove the resting mouth —
    // otherwise the pose swap silently no-ops (e.g. a typo'd char that never matches "E"/"M").
    assert.ok(!m.poses5.blink.some((row) => row.includes("E")), `${id}: blink still shows an open eye`);
    assert.ok(!m.poses5.sleep.some((row) => row.includes("E")), `${id}: sleep still shows an open eye`);
    assert.ok(!m.poses5.eat.some((row) => row.includes("M")), `${id}: eat still shows the resting mouth`);
  }
});
