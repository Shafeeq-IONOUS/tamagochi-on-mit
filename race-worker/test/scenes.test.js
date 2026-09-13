import { test } from "node:test";
import assert from "node:assert/strict";

import { COLS, LANE_COLS, OFF, ROWS, buildFrame, climbTop } from "../src/render.js";
import { FlashGuard, GUARD_FLASHES_PER_SECOND, MAX_FLASHES_PER_SECOND, worstFlashRate } from "../src/safety.js";
import {
  ANIMATED_STATUSES,
  DEFAULT_SCENE_CONFIG,
  INTRO_BEATS,
  countdownFrame,
  frameFor,
  introFrame,
  introducingAt,
  raceStartFrame,
  reignFrame,
  validateSceneConfig,
} from "../src/scenes.js";
import { showSequence } from "../scripts/sequence.js";
import { WIN_CELEBRATION_MS, winCelebrationFrame } from "../src/win-celebration.js";
import { SCHOOLS } from "../src/mascots.js";

const FPS = 15;
const INTRO_MS = DEFAULT_SCENE_CONFIG.introSeconds * 1000;

// The king is 9 rows tall and its ducklings walk under it, so the two overlap; these are the
// king's own rows, and the band where only an escort can still be once the king has left.
const KING_ROWS = [5, 8]; // KING_TOP .. DUCKLING_TOP - 1
const TRAIL_ROWS = [8, 14]; // DUCKLING_TOP - 1 .. DUCKLING_TOP + 5, bob included

const litColumns = (t, [from, to], champion = null) => {
  const grid = introFrame(t, { champion });
  const cols = new Set();
  for (let r = from; r < to; r++) for (let c = 0; c < COLS; c++) if (grid[r][c] !== OFF) cols.add(c);
  return cols;
};

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
  same(introFrame(INTRO_MS), countdownFrame(0)); // intro end = countdown before its first digit fades in
  same(countdownFrame(3000), raceStartFrame()); // countdown end = the race's first frame
  same(introFrame(20_000, { introSeconds: 20 }), raceStartFrame());
});

test("intro beats scale with the configured length", () => {
  // 40% into a 10 s and a 20 s intro show the same beat (the crown at the top). The river ripple
  // runs in real time on purpose, so the river row is left out.
  const beats = (grid) => grid.slice(0, ROWS - 1);
  assert.deepEqual(beats(introFrame(4000, { introSeconds: 10 })), beats(introFrame(8000, { introSeconds: 20 })));
});

test("countdown shows 3, 2, 1 and nothing for longer countdowns' early seconds", () => {
  const lit = (grid) => grid.slice(4, 9).flatMap((row) => row.slice(3, 6)).filter((px) => px[0] > 60).length;
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

test("mascots start on the riverbank and climb to the finish line", () => {
  assert.equal(climbTop(0), 13);
  assert.equal(climbTop(8), 1);
  const frame = buildFrame({ progressCols: { mit: 8, harvard: 4, bu: 0, neu: 2 }, status: "running", winner: null });
  const litRows = (col) => frame.map((row, r) => (row[col] === OFF ? null : r)).filter((r) => r !== null);
  assert.deepEqual(litRows(LANE_COLS[0]).slice(0, 4), [0, 1, 2, 3]); // MIT's mascot is under the finish line
  assert.equal(litRows(LANE_COLS[2]).at(1), 13); // BU hasn't left the riverbank (row 0 = finish line)
  assert.equal(frame[15][LANE_COLS[1]] !== OFF, true); // Harvard leaves a trail down to the river
  assert.equal(frame[8][4], OFF); // the gap column between Harvard and BU stays dark
});

test("every challenger is introduced, in lane order, before the countdown", () => {
  const seen = [];
  for (let t = 0; t <= INTRO_MS; t += 100) {
    const school = introducingAt(t);
    if (school && seen.at(-1) !== school) seen.push(school);
  }
  assert.deepEqual(seen, ["mit", "harvard", "bu", "neu"]);
  assert.equal(introducingAt(5000), null); // still the king's abdication
  assert.equal(introducingAt(INTRO_MS - 200), null); // everyone is on the riverbank
  // mid-introduction the mascot is shown big over a strip of its school colour
  const midMit = introFrame(INTRO_BEATS.introductions + 1500);
  assert.notDeepEqual(midMit[14][4], OFF);
  assert.ok(midMit.slice(5, 14).flat().filter((px) => px !== OFF).length > 30);
});

test("the Duck King's ducklings follow it off the tower", () => {
  assert.equal(litColumns(6600, TRAIL_ROWS).size > 0, true); // under the king, before it moves
  assert.equal(litColumns(9500, KING_ROWS).size, 0); // the king has already walked off, so
  assert.ok(litColumns(9600, TRAIL_ROWS).size >= 4); // what is still crossing is its escort
  // and they clear the building before the first challenger is introduced
  assert.equal(litColumns(INTRO_BEATS.introductions, TRAIL_ROWS).size, 0);
});

test("only the Duck King is escorted", () => {
  // a school mascot that won its way onto the throne abdicates alone, and walks the shorter
  // distance over the same beat, so by now it is gone and nothing trails it
  for (const champion of SCHOOLS) {
    assert.equal(litColumns(13_500, TRAIL_ROWS, champion).size, 0, `${champion} should have no ducklings`);
  }
  assert.ok(litColumns(13_500, TRAIL_ROWS).size > 0); // the Duck King still has its escort
});

test("config validation", () => {
  assert.deepEqual(validateSceneConfig({ introSeconds: "30" }), { introSeconds: 30, countdownSeconds: 3 });
  assert.throws(() => validateSceneConfig({ introSeconds: 13 }), RangeError); // too short to read
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

test("frameFor plays the win celebration for as long as \"finished\" persists, never settling", () => {
  const progressCols = Object.fromEntries(SCHOOLS.map((s) => [s, 8]));
  const base = { champion: null, config: DEFAULT_SCENE_CONFIG, phaseStartedAt: 0, winner: "mit", progressCols };
  // always matches winCelebrationFrame directly — mid-reveal, and long after (the looping phase)
  for (const t of [5000, WIN_CELEBRATION_MS + 1, WIN_CELEBRATION_MS * 5]) {
    assert.deepEqual(frameFor({ ...base, status: "finished" }, t), winCelebrationFrame(t, { winner: "mit", progressCols }));
  }
});

test("\"finished\" is an animated status, same as idle/intro/countdown", () => {
  assert.ok(ANIMATED_STATUSES.includes("finished"));
});

test("the whole show, including a full climb, is flash-safe", () => {
  for (const champion of [null, "mit", "harvard", "bu", "neu"]) {
    const raw = showSequence({ champion, fps: FPS, raceSeconds: 20 });
    const rawRate = worstFlashRate(raw, FPS);
    assert.ok(rawRate.rate <= MAX_FLASHES_PER_SECOND, `raw scenes flash ${rawRate.rate}/s at ${rawRate.where}`);

    const guard = new FlashGuard();
    const shown = raw.map((grid, i) => guard.filter(grid, (i * 1000) / FPS));
    const rate = worstFlashRate(shown, FPS);
    assert.ok(rate.rate <= GUARD_FLASHES_PER_SECOND, `guarded scenes flash ${rate.rate}/s at ${rate.where}`);
  }
});
