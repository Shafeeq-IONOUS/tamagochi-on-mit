import { test } from "node:test";
import assert from "node:assert/strict";

import { COLS, ROWS } from "../src/render.js";
import { FlashGuard, GUARD_FLASHES_PER_SECOND, MAX_FLASHES_PER_SECOND, worstFlashRate } from "../src/safety.js";
import {
  countdownFrame,
  frameFor,
  introFrame,
  raceStartFrame,
  reignFrame,
  validateSceneConfig,
} from "../src/scenes.js";
import { showSequence } from "../scripts/sequence.js";

const FPS = 15;

function assertValidGrid(grid) {
  assert.equal(grid.length, ROWS);
  for (const row of grid) {
    assert.equal(row.length, COLS);
    for (const px of row) {
      assert.equal(px.length, 3);
      for (const v of px) assert.ok(Number.isInteger(v) && v >= 0 && v <= 255, `bad channel ${v}`);
    }
  }
}

test("every scene frame is 17x9 RGB", () => {
  for (const champion of [null, "mit", "harvard", "bu", "neu"]) {
    for (let t = 0; t <= 12_000; t += 250) {
      assertValidGrid(reignFrame(t, { champion }));
      assertValidGrid(introFrame(t, { champion }));
      assertValidGrid(countdownFrame(t % 3000));
    }
  }
});

test("scene hand-offs don't jump", () => {
  const same = (a, b) => assert.deepEqual(a, b);
  same(introFrame(10_000), countdownFrame(3000)); // intro end = countdown without its digit
  same(countdownFrame(3000), raceStartFrame()); // countdown end = the race's first frame
  same(introFrame(20_000, { introSeconds: 20 }), raceStartFrame());
});

test("intro beats scale with the configured length", () => {
  // 40% into a 10 s and a 20 s intro show the same beat (crown melting into the banner). The bob,
  // blink and river ripple run in real time on purpose, so skip the river row and pick times
  // where the bob and blink line up.
  const beats = (grid) => grid.slice(0, ROWS - 1);
  assert.deepEqual(beats(introFrame(4000, { introSeconds: 10 })), beats(introFrame(8000, { introSeconds: 20 })));
});

test("countdown shows 3, 2, 1 and nothing for longer countdowns' early seconds", () => {
  const lit = (grid) => grid.slice(6, 11).flatMap((row) => row.slice(4, 7)).filter((px) => px[0] > 60).length;
  assert.ok(lit(countdownFrame(500, { countdownSeconds: 3 })) > 0);
  assert.equal(lit(countdownFrame(500, { countdownSeconds: 6 })), 0); // "6" isn't drawn
  assert.ok(lit(countdownFrame(3500, { countdownSeconds: 6 })) > 0);
});

test("frameFor follows the status", () => {
  const base = { champion: null, config: { introSeconds: 10, countdownSeconds: 3 }, phaseStartedAt: 0, winner: null };
  assert.deepEqual(frameFor({ ...base, status: "intro" }, 10_000), countdownFrame(3000));
  assert.deepEqual(frameFor({ ...base, status: "countdown" }, 3000), raceStartFrame());
  const progressCols = { mit: 0, harvard: 0, bu: 0, neu: 0 };
  assert.deepEqual(frameFor({ ...base, status: "running", progressCols }, 0), raceStartFrame());
});

test("config validation", () => {
  assert.deepEqual(validateSceneConfig({ introSeconds: "12" }), { introSeconds: 12, countdownSeconds: 3 });
  assert.throws(() => validateSceneConfig({ introSeconds: 1 }), RangeError);
  assert.throws(() => validateSceneConfig({ countdownSeconds: 11 }), RangeError);
  assert.throws(() => validateSceneConfig({ countdownSeconds: "soon" }), RangeError);
});

test("the guard stops a 10 Hz strobe", () => {
  const strobe = Array.from({ length: 60 }, (_, i) =>
    Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => (Math.floor(i / 1.5) % 2 ? [255, 255, 255] : [0, 0, 0]))),
  );
  assert.ok(worstFlashRate(strobe, 30).rate > MAX_FLASHES_PER_SECOND);
  const guard = new FlashGuard();
  const safe = strobe.map((grid, i) => guard.filter(grid, (i * 1000) / 30));
  assert.ok(worstFlashRate(safe, 30).rate <= GUARD_FLASHES_PER_SECOND);
});

test("reign -> intro -> countdown -> race start is flash-safe", () => {
  for (const champion of [null, "mit", "harvard", "bu", "neu"]) {
    const raw = showSequence({ champion, fps: FPS });
    const rawRate = worstFlashRate(raw, FPS);
    assert.ok(rawRate.rate <= MAX_FLASHES_PER_SECOND, `raw scenes flash ${rawRate.rate}/s at ${rawRate.where}`);

    const guard = new FlashGuard();
    const shown = raw.map((grid, i) => guard.filter(grid, (i * 1000) / FPS));
    const rate = worstFlashRate(shown, FPS);
    assert.ok(rate.rate <= GUARD_FLASHES_PER_SECOND, `guarded scenes flash ${rate.rate}/s at ${rate.where}`);
  }
});
