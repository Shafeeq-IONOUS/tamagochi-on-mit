// The story around the race, as pure (time, state) -> 17x9 frame functions.
//
//   idle       reign      the King of the Charles (the Duck King until someone wins) idles, crowned
//   intro      abdicate   see INTRO_BEATS below
//   countdown  3, 2, 1    soft digits while the challengers wait on the riverbank
//   running / finished    the climb itself (render.js)
//
// The last frame of each scene is the first frame of the next, so hand-offs don't jump.
import { SCHOOLS } from "./mascots.js";
import { BANNER, COLS, LANE_COLS, OFF, RIVER_ROW, ROWS, START_TOP, buildFrame, drawRiverRow } from "./render.js";
import { CROWN, DIGITS, GOLD, MASCOTS, MASCOT_FOR_SCHOOL, blank, blit, drawLaneMascot, mix } from "./sprites.js";

export const DEFAULT_SCENE_CONFIG = { introSeconds: 12, countdownSeconds: 3 };
// Below ~8 s the intro beats blur together on a building this size.
export const SCENE_CONFIG_LIMITS = { introSeconds: [8, 30], countdownSeconds: [0, 10] };
export const ANIMATED_STATUSES = ["idle", "intro", "countdown"];

// Beat boundaries in ms for a 12 s intro; they stretch or shrink with the configured length.
export const INTRO_BEATS = {
  holdEnd: 1500, //       0-1.5  the king, crowned, stands still
  bowEnd: 2500, //      1.5-2.5  bows: closes its eyes and dips one floor
  riseEnd: 4500, //     2.5-4.5  the crown lifts off, floor by floor, to the top of the tower
  shineEnd: 5500, //    4.5-5.5  the crown waits at the top
  meltEnd: 6500, //     5.5-6.5  the crown spreads into the gold finish line
  sinkEnd: 8500, //     6.5-8.5  the king sinks into the Charles
  riseChallengers: 9000, // 9.0-11.5 the four challengers climb out of the river, one by one
  end: 12000,
};

const KING_TOP = 5; // 9x9 king on rows 5-13, crown on rows 3-4
const CROWN_REST_TOP = KING_TOP - 2;
const RIPPLE = [30, 80, 140];
const DIGIT_COLOR = [150, 150, 150];
const DIGIT_TOP = 4; // rows 4-8, centred above the challengers
const CHALLENGER_STAGGER = 500;
const CHALLENGER_RISE = 1000;

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

function drawRiver(grid, t, { ripple = true } = {}) {
  drawRiverRow(grid);
  if (ripple) grid[RIVER_ROW][Math.floor(t / 700) % COLS] = RIPPLE;
}

function drawCrown(grid, top, alpha = 1) {
  blit(grid, CROWN.sprite, top, (COLS - 5) / 2, CROWN.colors, alpha);
}

function drawBanner(grid, color = BANNER) {
  for (let c = 0; c < COLS; c++) grid[0][c] = color;
}

/** Challengers on the riverbank; `rise` 0..1 per school (0 = still under the water). */
function drawChallengers(grid, rise = () => 1) {
  SCHOOLS.forEach((school, i) => {
    const k = ease(rise(i));
    if (k <= 0) return;
    drawLaneMascot(grid, school, LANE_COLS[i], Math.round(RIVER_ROW + 1 - k * (RIVER_ROW + 1 - START_TOP)));
  });
}

export function reignFrame(t, { champion = null } = {}) {
  const grid = blank(ROWS, COLS, OFF);
  const king = kingMascot(champion);
  const bob = t % 2000 < 1000 ? 0 : 1; // slow breathing
  const pose = t % 4000 > 3850 ? "blink" : "idle";
  blit(grid, king.poses[pose], KING_TOP - bob, 0, king.colors);
  drawCrown(grid, CROWN_REST_TOP - bob);
  drawRiver(grid, t);
  return grid;
}

export function introFrame(t, { champion = null, introSeconds = DEFAULT_SCENE_CONFIG.introSeconds } = {}) {
  const at = (ms) => (ms * introSeconds * 1000) / INTRO_BEATS.end;
  const b = Object.fromEntries(Object.entries(INTRO_BEATS).map(([k, ms]) => [k, at(ms)]));
  const grid = blank(ROWS, COLS, OFF);
  const king = kingMascot(champion);

  // the king: still, then a bow with closed eyes, then sinking below the river row
  const bow = Math.round(ease(progressBetween(t, b.holdEnd, b.bowEnd)));
  const sink = ease(progressBetween(t, b.meltEnd, b.sinkEnd));
  const kingTop = KING_TOP + bow + Math.round(sink * (ROWS - KING_TOP - bow));
  if (kingTop < RIVER_ROW) blit(grid, king.poses[t < b.holdEnd ? "idle" : "sleep"], kingTop, 0, king.colors);

  // the crown: lifts off to rows 0-1, waits, then spreads along row 0 into the finish line
  const crownTop = Math.round(CROWN_REST_TOP * (1 - ease(progressBetween(t, b.bowEnd, b.riseEnd))));
  const melt = ease(progressBetween(t, b.shineEnd, b.meltEnd));
  if (melt < 1) drawCrown(grid, crownTop, 1 - melt);
  if (melt > 0) {
    const reach = 2 + 2.5 * melt; // from the crown's width to the whole row
    for (let c = 0; c < COLS; c++) {
      if (Math.abs(c - (COLS - 1) / 2) <= reach) grid[0][c] = mix(GOLD, BANNER, melt);
    }
  }

  // the river rolls over the sinking king; it stills once the challengers start climbing out
  drawRiver(grid, t, { ripple: t < b.riseChallengers });
  drawChallengers(grid, (i) =>
    progressBetween(t, b.riseChallengers + at(i * CHALLENGER_STAGGER), b.riseChallengers + at(i * CHALLENGER_STAGGER + CHALLENGER_RISE)),
  );
  return grid;
}

export function countdownFrame(t, { countdownSeconds = DEFAULT_SCENE_CONFIG.countdownSeconds } = {}) {
  const grid = blank(ROWS, COLS, OFF);
  drawBanner(grid);
  drawRiver(grid, t, { ripple: false });
  drawChallengers(grid);

  const remaining = countdownSeconds * 1000 - t;
  const digit = Math.ceil(remaining / 1000);
  if (DIGITS[digit]) {
    const u = 1000 - (remaining - (digit - 1) * 1000); // 0..1000 within this digit's second
    const alpha = Math.max(0, Math.min(1, u / 250, (1000 - u) / 250));
    blit(grid, DIGITS[digit], DIGIT_TOP, (COLS - 3) / 2, { "#": DIGIT_COLOR }, alpha);
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
