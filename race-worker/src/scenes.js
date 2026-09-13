// The story around the race, as pure (time, state) -> 17x9 frame functions.
//
//   idle       reign      the King of the Charles (the Duck King until someone wins) idles, crowned
//   intro      abdicate   the king bows, the crown rises and melts into the finish banner,
//                         the king sinks into the Charles, the four challengers take their lanes
//   countdown  3, 2, 1    soft digits while the challengers wait at the start
//   running / finished    the race itself (render.js)
//
// The last countdown frame equals the race's first frame, so the hand-off has no jump.
import { SCHOOLS } from "./mascots.js";
import { BANNER_DIM, COLS, LANE_STARTS, OFF, ROWS, buildFrame } from "./render.js";
import { CROWN, DIGITS, GOLD, MASCOTS, MASCOT_FOR_SCHOOL, blank, blit, mix } from "./sprites.js";

export const DEFAULT_SCENE_CONFIG = { introSeconds: 10, countdownSeconds: 3 };
export const SCENE_CONFIG_LIMITS = { introSeconds: [3, 30], countdownSeconds: [0, 10] };
export const ANIMATED_STATUSES = ["idle", "intro", "countdown"];

const KING_TOP = 5; // 9x9 king on rows 5-13, crown on rows 3-4
const RIVER_ROW = ROWS - 1;
const RIVER = [0, 35, 80];
const RIPPLE = [30, 80, 140];
const DIGIT_COLOR = [150, 150, 150];
const INTRO_REFERENCE_MS = 10_000; // beat times below are for a 10 s intro and scale with it

const ease = (x) => 0.5 - 0.5 * Math.cos(Math.PI * Math.max(0, Math.min(1, x)));
const progressBetween = (t, start, end) => Math.max(0, Math.min(1, (t - start) / (end - start)));

export function validateSceneConfig(input = {}, base = DEFAULT_SCENE_CONFIG) {
  const out = { ...base };
  for (const [key, [min, max]] of Object.entries(SCENE_CONFIG_LIMITS)) {
    if (input[key] === undefined) continue;
    const value = Number(input[key]);
    if (!Number.isFinite(value) || value < min || value > max) {
      throw new RangeError(`${key} must be between ${min} and ${max} seconds`);
    }
    out[key] = value;
  }
  return out;
}

const kingMascot = (champion) => MASCOTS[MASCOT_FOR_SCHOOL[champion] ?? "duck"];

function drawRiver(grid, t, alpha = 1) {
  const ripple = Math.floor(t / 700) % COLS;
  for (let c = 0; c < COLS; c++) {
    grid[RIVER_ROW][c] = mix(OFF, c === ripple ? RIPPLE : RIVER, alpha);
  }
}

function drawCrown(grid, top, alpha = 1) {
  blit(grid, CROWN.sprite, top, (COLS - 5) / 2, CROWN.colors, alpha);
}

/** Idle king with crown; `t` drives the breathing bob and the blink. */
function drawKing(grid, mascot, t, { top = KING_TOP, alpha = 1, crown = true } = {}) {
  const bob = t % 2000 < 1000 ? 0 : 1;
  const pose = t % 4000 > 3850 ? "blink" : "idle";
  blit(grid, mascot.poses[pose], top - bob, 0, mascot.colors, alpha);
  if (crown) drawCrown(grid, top - bob - 2, alpha);
}

function drawChallengers(grid, t = Infinity, enterAt = 0, stagger = 400, duration = 1200) {
  SCHOOLS.forEach((school, i) => {
    const k = ease(progressBetween(t, enterAt + i * stagger, enterAt + i * stagger + duration));
    if (k <= 0) return;
    // slide in from just off the left edge (drawLaneMascot clamps to the grid, so blit directly)
    const m = MASCOTS[MASCOT_FOR_SCHOOL[school]];
    blit(grid, m.mini, LANE_STARTS[i], Math.round(-2 + 2 * k), m.colors, k);
  });
}

function drawBanner(grid, color = BANNER_DIM) {
  for (let c = 0; c < COLS; c++) grid[0][c] = color;
}

export function reignFrame(t, { champion = null } = {}) {
  const grid = blank(ROWS, COLS, OFF);
  drawKing(grid, kingMascot(champion), t);
  drawRiver(grid, t);
  return grid;
}

export function introFrame(t, { champion = null, introSeconds = DEFAULT_SCENE_CONFIG.introSeconds } = {}) {
  const s = (introSeconds * 1000) / INTRO_REFERENCE_MS;
  const at = (ms) => ms * s;
  const grid = blank(ROWS, COLS, OFF);
  const king = kingMascot(champion);

  // 1.5-3.5 s: bow one floor while the crown rises to the roof
  const bow = Math.round(ease(progressBetween(t, at(1500), at(2500))));
  // 5-6.5 s: sink into the Charles
  const sink = ease(progressBetween(t, at(5000), at(6500)));
  const kingTop = KING_TOP + bow + Math.round(sink * (ROWS - KING_TOP));
  if (sink < 1) drawKing(grid, king, t, { top: kingTop, alpha: 1 - sink, crown: false });

  // crown: sits on the head, rises to rows 0-1, then melts into the finish banner
  const rise = ease(progressBetween(t, at(1500), at(3500)));
  const melt = ease(progressBetween(t, at(3500), at(5000)));
  if (melt < 1) {
    const headTop = KING_TOP - (t % 2000 < 1000 ? 0 : 1) - 2;
    drawCrown(grid, Math.round(headTop * (1 - rise)), 1 - melt);
  }
  if (melt > 0) {
    const half = Math.round(2 + 2.5 * melt); // spreads from the crown's width to the full row
    const color = mix(GOLD, BANNER_DIM, melt);
    for (let c = 0; c < COLS; c++) {
      if (Math.abs(c - (COLS - 1) / 2) <= half) grid[0][c] = mix(grid[0][c], color, Math.min(1, melt * 2));
    }
  }

  // 6.5-10 s: challengers take their lanes; the river fades so the race starts on a clean facade
  drawChallengers(grid, t, at(6500), at(400), at(1200));
  drawRiver(grid, t, 1 - progressBetween(t, at(8500), at(10000)));
  return grid;
}

export function countdownFrame(t, { countdownSeconds = DEFAULT_SCENE_CONFIG.countdownSeconds } = {}) {
  const grid = blank(ROWS, COLS, OFF);
  drawBanner(grid);
  drawChallengers(grid);

  const remaining = countdownSeconds * 1000 - t;
  const digit = Math.ceil(remaining / 1000);
  if (DIGITS[digit]) {
    const u = 1000 - (remaining - (digit - 1) * 1000); // 0..1000 within this digit's second
    const alpha = Math.max(0, Math.min(1, u / 250, (1000 - u) / 250));
    blit(grid, DIGITS[digit], 6, 4, { "#": DIGIT_COLOR }, alpha);
  }
  return grid;
}

/** The first frame of the race, for the hand-off check. */
export function raceStartFrame() {
  return buildFrame({ progressCols: Object.fromEntries(SCHOOLS.map((s) => [s, 0])), status: "running", winner: null });
}

/** Whatever the building should show for `state` at `now` (ms since epoch). */
export function frameFor(state, now) {
  const t = Math.max(0, now - (state.phaseStartedAt ?? now));
  const config = state.config ?? DEFAULT_SCENE_CONFIG;
  switch (state.status) {
    case "idle":
      return reignFrame(now, state); // absolute time so the bob doesn't restart on every reload
    case "intro":
      return introFrame(t, { ...config, champion: state.champion });
    case "countdown":
      return countdownFrame(t, config);
    default:
      return buildFrame(state);
  }
}
