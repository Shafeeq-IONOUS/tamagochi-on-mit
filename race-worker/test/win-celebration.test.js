import { test } from "node:test";
import assert from "node:assert/strict";

import { COLS, ROWS, buildFrame } from "../src/render.js";
import { FlashGuard, GUARD_FLASHES_PER_SECOND, worstFlashRate } from "../src/safety.js";
import { WIN_CELEBRATION_MS, winCelebrationFrame } from "../src/win-celebration.js";
import { SCHOOLS } from "../src/mascots.js";

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

const progressCols = Object.fromEntries(SCHOOLS.map((s) => [s, 8]));

test("winCelebrationFrame is a well-formed grid across the whole ~18.4s duration, for every winner", () => {
  for (const winner of SCHOOLS) {
    for (let t = 0; t <= WIN_CELEBRATION_MS; t += 200) {
      assertValidGrid(winCelebrationFrame(t, { winner, progressCols }));
    }
  }
});

test("the celebration's first frame is exactly today's static finished frame", () => {
  for (const winner of SCHOOLS) {
    assert.deepEqual(
      winCelebrationFrame(0, { winner, progressCols }),
      buildFrame({ progressCols, status: "finished", winner }),
    );
  }
});

test("the celebration draws the winner's crowned mascot during the mascot phase", () => {
  const grid = winCelebrationFrame(WIN_CELEBRATION_MS - 100, { winner: "mit", progressCols });
  const lit = grid.flat().filter((px) => px[0] > 30 || px[1] > 30 || px[2] > 30);
  assert.ok(lit.length > 40, "mascot phase looks empty");
});

test("the win celebration stays inside the same flash budget as the rest of the show", () => {
  const FPS = 15; // matches SCENE_FPS in race-state.js
  // 2.5 cycles: the celebration now loops forever, so this deliberately crosses the loop
  // seam (where the mascot phase wraps back to its own t=0) at least once — the blink cycle
  // (3.333s) doesn't divide evenly into the mascot phase (15s), so the seam is a real content
  // discontinuity, not just a repeat; confirm the guard smooths it the same as any other cut.
  const total = Math.round(((WIN_CELEBRATION_MS * 2.5) / 1000) * FPS);
  for (const winner of SCHOOLS) {
    const guard = new FlashGuard();
    const frames = [];
    for (let i = 0; i < total; i++) {
      const now = (i * 1000) / FPS;
      frames.push(guard.filter(winCelebrationFrame(now, { winner, progressCols }), now));
    }
    const rate = worstFlashRate(frames, FPS);
    assert.ok(rate.rate <= GUARD_FLASHES_PER_SECOND, `${winner} flashes ${rate.rate}/s at ${rate.where}`);
  }
});

test("the celebration keeps producing valid frames indefinitely (loops, never stops)", () => {
  for (const winner of SCHOOLS) {
    for (const t of [WIN_CELEBRATION_MS * 3, WIN_CELEBRATION_MS * 10 + 4321]) {
      assertValidGrid(winCelebrationFrame(t, { winner, progressCols }));
    }
  }
});
