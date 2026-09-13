// The automatic win celebration: an ~18.4s sequence that plays once a race is won, ported
// from `tamagochi-mascots-python/race.py`'s Renderer (branch `ananya`) onto this repo's
// (t, opts) -> 17x9 grid convention (see scenes.js). Three phases, exactly race.py's own
// PHASES/NEXT_PHASE chain "flash" -> "expand" -> "mascot":
//   flash    1.4s   the frozen finish-line frame: the winner's lane crossfades to white,
//                   everything else fades to black
//   expand   2.0s   the winner's colour sweeps sideways to fill the whole facade, a bright
//                   leading edge, scattered sparks
//   mascot  15.0s   the winner's mascot, crowned, on a dim wash of its colour, confetti
//                   falling from the roof
//
// NOT ported as-is: race.py's `mascot -> reign` auto-loop (it restarts a fresh race on a
// clock; this repo's race only advances when a host presses Start, so there's no clock to
// loop back to reign on). Instead, `winCelebrationFrame` plays the one-shot reveal (flash,
// then expand) once, then loops the mascot/confetti phase forever — `status` stays
// "finished" until the next start()/reset(), and scenes.js's `ANIMATED_STATUSES` keeps this
// module's frames streaming for exactly as long as that lasts, the same way "idle" loops
// the reign forever. (WIN_CELEBRATION_MS is still useful as "how long the one-shot reveal
// plus one mascot-phase cycle takes" for tests, but nothing settles or stops at that point.)
//
// PARTICLE SIMPLIFICATION: race.py's sparks/confetti are a per-tick RNG process tied to a
// stateful Renderer (`self.bits`, appended/aged once per render() call). This file is a pure
// (t) -> grid function, so each particle system is reinterpreted as N fixed emitters with
// golden-ratio-hashed positions, spread across the phase — the same deterministic stand-in
// for a Poisson process that living-field-scenes.js's finaleFrame already uses for its embers.
// Counts/periods below approximate the source's visual density; they're a tuning knob, not
// a exact match, same spirit as this repo's other "tune to taste" constants.

import { SCHOOLS, SCHOOL_INFO } from "./mascots.js";
import { COLS, LANE_COLS, ROWS, buildFrame, softenColor } from "./render.js";
import { CROWN, GOLD, MASCOTS, MASCOT_FOR_SCHOOL, WHITE, blank, blit, mix, scale } from "./sprites.js";

const FLASH_MS = 1400;
const EXPAND_MS = 2000;
const MASCOT_MS = 15000;
export const WIN_CELEBRATION_MS = FLASH_MS + EXPAND_MS + MASCOT_MS; // 18400 — race.py's 1.4 + 2.0 + 15.0

const clamp01 = (v) => Math.max(0, Math.min(1, v));
const clampByte = (v) => Math.max(0, Math.min(255, Math.round(v)));
const add = (base, color, alpha = 1) => base.map((v, i) => clampByte(v + color[i] * alpha)); // race.py's Frame.add

function laneCols(winner) {
  const left = LANE_COLS[SCHOOLS.indexOf(winner)];
  return [left, left + 1];
}

// -- FLASH: race.py Renderer._flash --------------------------------------------------------
// p = t / 1.4s. Starts from the frozen final race frame (render.js's buildFrame, which already
// draws the winner-coloured finish line — this repo's equivalent of race.py's `_race(..., t=0,
// winner=...)` freeze). The winner's two lane columns (all 17 rows) crossfade PER-PIXEL from
// their own frozen-frame colour to WHITE, reaching pure white by p = 1/1.6 (~0.875s in);
// everything else scales toward black, reaching pure black at p=1. Mixing from each pixel's
// own colour (rather than flooding the lane with a flat winner-colour block) is what makes
// p=0 reduce to an exact no-op over the whole frame, not just the finish line row — see the
// continuity check below.
function flashFrame(t, { winner, progressCols }) {
  const p = clamp01(t / FLASH_MS);
  const base = buildFrame({ progressCols, status: "finished", winner });
  const [left, right] = laneCols(winner);
  const k = Math.min(1, 1.6 * p);
  return base.map((row) => row.map((px, c) => (c === left || c === right ? mix(px, WHITE, k) : scale(px, Math.max(0, 1 - p)))));
}

// -- EXPAND: race.py Renderer._expand + sparks ----------------------------------------------
const SPARK_COUNT = 24; // race.py spawns ~18/s (p=0.6 per tick @ ~30fps); this approximates the density
const SPARK_LIFE_MS = 480; // race.py: life 1.0 decaying 0.07/tick @ ~30fps ≈ 476ms
function sparkAt(k, t, winColor) {
  const spawnAt = (k / SPARK_COUNT) * EXPAND_MS;
  const local = t - spawnAt;
  if (local < 0 || local >= SPARK_LIFE_MS) return null;
  const col = Math.floor(((k * 0.6180339887 + 0.13) % 1) * COLS);
  const row = Math.floor(((k * 0.7548776662 + 0.31) % 1) * ROWS);
  return { row, col, color: mix(WHITE, winColor, 0.3), alpha: 1 - local / SPARK_LIFE_MS };
}

function expandFrame(t, { winner }) {
  const p = clamp01(t / EXPAND_MS);
  const winColor = softenColor(SCHOOL_INFO[winner].color);
  const [left, right] = laneCols(winner);
  const reach = p * (COLS + 1);
  const grid = blank(ROWS, COLS, [0, 0, 0]);
  for (let c = 0; c < COLS; c++) {
    const distance = Math.min(Math.abs(c - left), Math.abs(c - right));
    if (distance > reach) continue;
    const px = mix(winColor, WHITE, 0.55 * Math.max(0, 1 - (reach - distance)));
    for (let r = 0; r < ROWS; r++) grid[r][c] = px;
  }
  for (let k = 0; k < SPARK_COUNT; k++) {
    const s = sparkAt(k, t, winColor);
    if (s) grid[s.row][s.col] = add(grid[s.row][s.col], s.color, s.alpha);
  }
  return grid;
}

// -- MASCOT: race.py Renderer._mascot + confetti ---------------------------------------------
const WIN_MASCOT_TOP = 8; // race.py's MASCOT_TOP: the 9x9 mascot's feet sit on the bottom row (16)
const CROWN_TOP = WIN_MASCOT_TOP - 2; // race.py's CROWN_TOP
const SKY_ROW = CROWN_TOP; // confetti falls until it reaches the crown, then "lands" (stops drawing)
const FALL_FLOORS_PER_SEC = 1.5; // race.py's confetti fall speed
const CONFETTI_COUNT = 16; // race.py spawns ~3/s (p=0.10/tick @ ~30fps) over 15s
const FALL_MS = ((SKY_ROW + 1) / FALL_FLOORS_PER_SEC) * 1000; // time from row -1 to SKY_ROW
const CONFETTI_GAP_MS = 500; // pause before a slot's next drop; without this it's a single burst
const CONFETTI_PERIOD_MS = FALL_MS + CONFETTI_GAP_MS;
const BLINK_PERIOD_MS = 3333; // race.py: blink when frame-count % 100 < 10, @ ~30fps ≈ 3.33s/0.33s
const BLINK_MS = 333;

function confettiAt(k, t, winColor) {
  const offset = (k / CONFETTI_COUNT) * CONFETTI_PERIOD_MS;
  const shifted = t + offset;
  const local = shifted % CONFETTI_PERIOD_MS;
  if (local >= FALL_MS) return null;
  const loop = Math.floor(shifted / CONFETTI_PERIOD_MS);
  const col = Math.floor((((k + loop * 7) * 0.6180339887 + 0.17) % 1) * COLS);
  const palette = [winColor, GOLD, WHITE]; // race.py: rng.choice([win.color, GOLD, WHITE])
  const row = Math.floor(-1 + (local / 1000) * FALL_FLOORS_PER_SEC);
  return row >= 0 && row < SKY_ROW ? { row, col, color: palette[(k + loop) % 3] } : null;
}

function mascotFrame(t, { winner }) {
  const winColor = softenColor(SCHOOL_INFO[winner].color);
  const wash = scale(winColor, 0.1); // race.py: the whole facade tinted 10% of the winner's colour
  const grid = blank(ROWS, COLS, wash);
  for (let k = 0; k < CONFETTI_COUNT; k++) {
    const c = confettiAt(k, t, winColor);
    if (c) grid[c.row][c.col] = add(grid[c.row][c.col], c.color, 1); // full-alpha, matches race.py
  }
  blit(grid, CROWN.sprite, CROWN_TOP, (COLS - 5) / 2, CROWN.colors);
  const mascot = MASCOTS[MASCOT_FOR_SCHOOL[winner]];
  const pose = t % BLINK_PERIOD_MS < BLINK_MS ? "blink" : "idle";
  blit(grid, mascot.poses[pose], WIN_MASCOT_TOP, 0, mascot.colors);
  return grid;
}

/** Whatever the building should show `t` ms after a win. Plays the one-shot reveal (flash,
 * then expand) once, then loops the crowned-mascot/confetti phase forever — the race only
 * leaves "finished" when a host presses Start, so there's no natural moment to stop
 * animating and settle onto a static frame. (An earlier version tried to settle after
 * WIN_CELEBRATION_MS; since FlashGuard slews color changes gradually and only one frame got
 * pushed at that point, it froze mid-transition — a muted, half-blended frame that never
 * finished converging. Looping forever means frames never stop coming, so FlashGuard always
 * has a live target to converge toward.) */
export function winCelebrationFrame(t, opts = {}) {
  const clamped = Math.max(0, t);
  if (clamped < FLASH_MS) return flashFrame(clamped, opts);
  let a = clamped - FLASH_MS;
  if (a < EXPAND_MS) return expandFrame(a, opts);
  return mascotFrame((a - EXPAND_MS) % MASCOT_MS, opts);
}
