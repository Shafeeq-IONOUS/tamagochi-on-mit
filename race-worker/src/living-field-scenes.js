// Curated ports of a handful of behaviours from the `living_field` Python prototype
// (branch `living-field`, tamagochi-characters-python/living_field/) onto this repo's
// plain-JS, 0-255-int, 17x9 pure `(t, opts) -> grid` convention — same shape as scenes.js.
//
// PORTED
//   finale   the winner's fireworks (race.py `finale()`) — an ~11s, four-movement
//            sequence explicitly called out by living_field's README as "worth
//            stealing regardless of the rest" and a good fit for a race winner.
//   aurora   vertical curtains of light (patterns.py `aurora()` + worlds.py's AURORA ramp)
//   seismic  a wave travelling up through the tower (patterns.py `seismic()` + SEISMIC ramp)
//   radar    the weather-radar dome on the roof, sweeping (patterns.py `radar()` + RADAR ramp)
//
// These four were picked because they are pure functions of a clock (no crowd/touch state
// to fake), visually distinct in *shape* (not just palette), and cheap per-pixel.
//
// DELIBERATELY NOT PORTED
//   - race.py's Race/Crew classes: living_field's own README says to throw the rest of
//     race.py away in favor of this repo's race-state.js/render.js, which already exist
//     and are better (real state, real mascots, a front end).
//   - attention / startle / memory / dream (patterns.py): these take a `ctx` of recent
//     touches and a tracked gaze point — reactive/stateful, not pure (t) -> frame like
//     everything else here, and this repo has no crowd-position sensor to feed them.
//   - forecast (patterns.py) / weather.py: needs a live NWS fetch. living_field's README
//     spends real effort making that fetch never block or fail loudly (background thread,
//     on-disk cache, silent failure); replicating that machinery is out of scope for a
//     "preview button" here, and it would be the one scene that depends on network being up.
//   - tree.py: a whole extra stateful subsystem (branches grafted by a crowd across an
//     entire evening, persisted); far bigger than the "small, curated handful" this task
//     asked for.
//   - sounding, reef: sounding is a vertical banded column much like aurora in spirit
//     (skipped for variety, not difficulty); reef is a reaction-diffusion simulation that
//     carries its own state across frames rather than being a pure function of time.
//
// SIMPLIFICATION NOTE
// The Python originals render on a 4x supersampled grid purely for antialiasing, then
// average down to 17x9, and compose through worlds.py's substrate/texture/breathing/
// ripple-boost system with gamma-correct colour ramps (ramps.py: un-squash sRGB, mix in
// linear light, squash back). This file computes directly at the real 17x9 resolution —
// scenes.js doesn't supersample either, so this matches the rest of the repo — and blends
// ramp colours with plain linear RGB interpolation via sprites.js's `mix()`, the same way
// scenes.js blends colours everywhere else. The shapes and motion match the originals;
// the exact tonal curve does not, and that trade felt right for a debug preview rather
// than a pixel-exact port.
import { COLS, ROWS } from "./render.js";
import { blank, mix } from "./sprites.js";

const TAU = Math.PI * 2;
const clamp01 = (v) => Math.max(0, Math.min(1, v));
const clampByte = (v) => Math.max(0, Math.min(255, Math.round(v)));

/** stops: [[pos 0..1, [r,g,b] 0..255], ...] sorted by pos. Plain (non-gamma) RGB lerp. */
function sampleRamp(stops, pos) {
  const p = clamp01(pos);
  for (let i = 1; i < stops.length; i++) {
    const [p0, c0] = stops[i - 1];
    const [p1, c1] = stops[i];
    if (p <= p1 || i === stops.length - 1) {
      const t = p1 > p0 ? (p - p0) / (p1 - p0) : 0;
      return mix(c0, c1, clamp01(t));
    }
  }
  return stops[stops.length - 1][1];
}

// -- colour ramps, transcribed from living_field/ramps.py -------------------------------
const AURORA_RAMP = [
  [0.0, [4, 16, 26]],
  [0.26, [8, 78, 56]],
  [0.55, [48, 214, 118]],
  [0.8, [150, 250, 178]],
  [1.0, [214, 104, 235]],
];
const SEISMIC_RAMP = [
  [0.0, [14, 6, 12]],
  [0.3, [96, 18, 32]],
  [0.6, [214, 74, 28]],
  [0.82, [246, 158, 44]],
  [1.0, [255, 232, 170]],
];
const RADAR_RAMP = [
  [0.0, [2, 14, 22]],
  [0.22, [14, 108, 74]],
  [0.45, [54, 186, 96]],
  [0.64, [206, 220, 62]],
  [0.82, [238, 146, 42]],
  [1.0, [228, 58, 66]],
];

// -- ambient patterns, transcribed from living_field/patterns.py ------------------------
// Each fills the whole 17x9 facade from `t` (ms) alone; `y`/`x` below are 0..1, y=0 at the
// roof (row 0) same as this repo's own grids.

/** AURORA — vertical curtains of light that fold and drift sideways as they descend. */
export function auroraFrame(t) {
  const tS = t / 1000;
  const grid = blank(ROWS, COLS, [0, 0, 0]);
  for (let r = 0; r < ROWS; r++) {
    const y = (r + 0.5) / ROWS;
    const lean = 0.16 * Math.sin(TAU * (y * 0.9 + tS * 0.055)) + 0.07 * Math.sin(TAU * (y * 2.1 - tS * 0.031));
    for (let c = 0; c < COLS; c++) {
      const x = (c + 0.5) / COLS;
      let v = Math.sin(TAU * ((x + lean) * 2.1 + tS * 0.021));
      v = Math.sign(v) * Math.abs(v) ** 0.65; // sharpen into distinct sheets
      v *= 1.15 - 0.85 * y; // hangs from the top
      grid[r][c] = sampleRamp(AURORA_RAMP, (v + 1) / 2);
    }
  }
  return grid;
}

/** SEISMIC — long calm, then a hard bright front climbing the tower, then a ragged tail. */
export function seismicFrame(t) {
  const tS = t / 1000;
  const period = 17;
  const phase = (((tS % period) + period) % period) / period;
  const front = 1.12 - phase * 1.55; // travels ground -> roof
  const grid = blank(ROWS, COLS, [0, 0, 0]);
  for (let r = 0; r < ROWS; r++) {
    const y = (r + 0.5) / ROWS;
    const d = y - front;
    const pWave = Math.exp(-(d * d) / (2 * 0.03 ** 2));
    const sWave = 0.75 * Math.exp(-((d - 0.155) ** 2) / (2 * 0.085 ** 2));
    const codaEnv = 0.3 * Math.exp(-Math.max(d - 0.28, 0) / 0.35);
    const coda = codaEnv * Math.sin(TAU * (y * 9.0 - tS * 1.1));
    const quiet = 0.06 * Math.sin(TAU * (y * 2.0 + tS * 0.08));
    let v = pWave + sWave + coda + quiet;
    v = v * 1.5 - 0.28;
    const color = sampleRamp(SEISMIC_RAMP, (v + 1) / 2);
    for (let c = 0; c < COLS; c++) grid[r][c] = color; // seismic is uniform across columns
  }
  return grid;
}

/** RADAR — the weather-radar dome on the roof, sweeping a sector scan back and forth. */
export function radarFrame(t) {
  const tS = t / 1000;
  const period = 9;
  const swing = Math.sin(TAU * (tS / period));
  const ang = swing * 1.1; // about +/- 63 degrees
  const goingRight = Math.cos(TAU * (tS / period)) > 0;
  const grid = blank(ROWS, COLS, [0, 0, 0]);
  for (let r = 0; r < ROWS; r++) {
    const y = (r + 0.5) / ROWS;
    const dy = y + 0.03; // origin sits on the roof
    for (let c = 0; c < COLS; c++) {
      const x = (c + 0.5) / COLS;
      const dx = x - 0.5;
      const a = Math.atan2(dx, dy);
      const da = a - ang;
      const beam = Math.exp(-(da * da) / (2 * 0.13 ** 2));
      const behind = goingRight ? da : -da;
      const trail = 0.55 * Math.exp(-Math.max(behind, 0) / 0.42); // the echo lingers behind the beam
      const dist = Math.sqrt(dx * dx + dy * dy);
      let v = (beam + trail) * (0.4 + 0.8 * dist);
      v = v * 1.7 - 0.38;
      grid[r][c] = sampleRamp(RADAR_RAMP, (v + 1) / 2);
    }
  }
  return grid;
}

// -- finale, transcribed from living_field/race.py's finale() ---------------------------
// Eleven seconds, four movements: LAUNCH (rocket climbs the winner's lane), BURST (three
// shells open across the facade), FALL (embers drift down, the roof holds a glow), NAME
// (settles to a soft breathing glow — the tower would say who won here; that's left to the
// caller/UI, same as the Python original left the name to run.py).
const LAUNCH_S = 1.6;
const BURST_S = 2.9;
const FALL_S = 3.5;
const NAME_S = 3.0;
export const FINALE_SECONDS = LAUNCH_S + BURST_S + FALL_S + NAME_S; // 11.0

const WARM_TINT = [0.45, 0.35, 0.18];
const warmOf = (col01) => col01.map((v, i) => clamp01(v * 0.55 + WARM_TINT[i]));

/**
 * FINALE — the winner's fireworks. `t` is ms since the crew crossed the line.
 * `color`: winner's RGB (0-255). `lane`: 0..1 across the facade, where the rocket launches
 * from (defaults to the Duck King's gold, centred, when there's no specific winner).
 */
export function finaleFrame(t, { color = [210, 160, 20], lane = 0.5 } = {}) {
  const age = Math.max(0, t / 1000);
  const col = color.map((v) => v / 255);
  const warm = warmOf(col);
  const acc = Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => [0, 0, 0]));
  const add = (r, c, factor, rgb) => {
    if (factor <= 0) return;
    const px = acc[r][c];
    px[0] += factor * rgb[0];
    px[1] += factor * rgb[1];
    px[2] += factor * rgb[2];
  };
  const toGrid = () => acc.map((row) => row.map(([r, g, b]) => [clampByte(r * 255), clampByte(g * 255), clampByte(b * 255)]));

  if (age < LAUNCH_S) {
    // A rocket leaving the winner's lane, fast in space (which is fine — windows just can't
    // blink), trailing behind it.
    const p = age / LAUNCH_S;
    const y0 = 1.0 - p * 0.86;
    for (let r = 0; r < ROWS; r++) {
      const y = (r + 0.5) / ROWS;
      const dy = y - y0;
      for (let c = 0; c < COLS; c++) {
        const x = (c + 0.5) / COLS;
        const dx = Math.abs(x - lane);
        const head = Math.exp(-(dy * dy) / (2 * 0.03 ** 2)) * Math.exp(-(dx * dx) / (2 * 0.055 ** 2));
        const trail = Math.exp(-Math.max(dy, 0) / 0.3) * Math.exp(-(dx * dx) / (2 * 0.045 ** 2)) * 0.5;
        add(r, c, (head * 1.7 + trail) * (0.4 + 0.6 * p), col);
      }
    }
    return toGrid();
  }

  let a = age - LAUNCH_S;
  if (a < BURST_S) {
    // Three shells, staggered, each swelling open rather than popping.
    const p = a / BURST_S;
    const shells = [
      [0.5, 0.16, 0.0, 1.0],
      [0.26, 0.3, 0.55, 0.72],
      [0.76, 0.26, 0.95, 0.78],
    ];
    for (let r = 0; r < ROWS; r++) {
      const y = (r + 0.5) / ROWS;
      for (let c = 0; c < COLS; c++) {
        const x = (c + 0.5) / COLS;
        shells.forEach(([cx, cy, delay, size], k) => {
          const local = a - delay;
          if (local <= 0) return;
          const q = Math.min(1.0, local / (BURST_S - delay));
          const rad = 0.06 + size * 0.75 * q ** 0.55;
          const d = Math.hypot(x - cx, y - cy);
          const shell = Math.exp(-((d - rad) ** 2) / (2 * (0.055 + 0.1 * q) ** 2));
          const core = Math.exp(-(d * d) / (2 * (0.1 + 0.16 * q) ** 2)) * (1.0 - q);
          const fade = (1.0 - q) ** 0.7;
          add(r, c, (shell * 1.25 + core * 1.1) * fade, k === 0 ? col : warm);
        });
        add(r, c, 0.16 * (1.0 - p), col); // the whole facade carries the colour while it's open
      }
    }
    return toGrid();
  }

  a -= BURST_S;
  if (a < FALL_S) {
    // Embers drifting down; the roof holds a glow.
    const p = a / FALL_S;
    for (let r = 0; r < ROWS; r++) {
      const y = (r + 0.5) / ROWS;
      for (let c = 0; c < COLS; c++) {
        const x = (c + 0.5) / COLS;
        let fall = 0;
        for (let i = 0; i < 9; i++) {
          const sx = (i * 0.113 + 0.07) % 1.0;
          const sy = 0.16 + 0.8 * p ** 1.35 + 0.1 * Math.sin(i * 2.1);
          const dx = x - sx;
          const dy = y - sy;
          fall = Math.max(fall, Math.exp(-(dx * dx) / (2 * 0.035 ** 2) - (dy * dy) / (2 * 0.045 ** 2)));
        }
        const drift = fall * (1.0 - p) * 1.15;
        const roof = Math.exp(-(y * y) / (2 * 0.3 ** 2)) * 0.42 * (1.0 - p * 0.7);
        add(r, c, drift, warm);
        add(r, c, roof, col);
      }
    }
    return toGrid();
  }

  // Settling into a soft, held, breathing glow.
  a -= FALL_S;
  const p = Math.min(1.0, a / NAME_S);
  const glow = 0.3 * (1.0 - p * 0.55) * (0.85 + 0.15 * Math.sin(TAU * 0.5 * age));
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) add(r, c, glow, col);
  return toGrid();
}

/** Admin debug registry: one entry per previewable living-field scene. */
export const LIVING_FIELD_SCENES = {
  finale: { label: "Finale (fireworks)", seconds: FINALE_SECONDS, frame: finaleFrame },
  aurora: { label: "Aurora", seconds: 8, frame: (t) => auroraFrame(t) },
  seismic: { label: "Seismic", seconds: 17, frame: (t) => seismicFrame(t) },
  radar: { label: "Radar", seconds: 9, frame: (t) => radarFrame(t) },
};
