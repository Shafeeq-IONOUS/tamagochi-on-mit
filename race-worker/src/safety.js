// Photosensitivity guard for a building-sized display.
//
// WCAG 2.3.1: nothing may flash more than 3 times in any 1 second. A flash is a pair of
// opposing changes in relative luminance of 10% or more where the darker state is below 0.8.
// A whole facade is a very large visual field, so the guard enforces a stricter budget, on
// every window and on the facade average:
//   1. Slew: each R/G/B moves at most MAX_STEP per frame (hard cuts become short fades).
//   2. Reversal budget: a change that would exceed GUARD_FLASHES_PER_SECOND is held back.
// Scenes should still avoid flashy effects instead of leaning on the guard.

export const MAX_FLASHES_PER_SECOND = 3;
export const GUARD_FLASHES_PER_SECOND = 2;
const FLASH_DELTA = 0.1;
const DARK_BELOW = 0.8;
const RAMP_SECONDS = 0.3; // a 0 -> 255 fade takes at least this long at the reference fps
const REFERENCE_FPS = 30;

const LINEAR = Array.from({ length: 256 }, (_, v) => {
  const s = v / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
});

export function luminance([r, g, b]) {
  return 0.2126 * LINEAR[r] + 0.7152 * LINEAR[g] + 0.0722 * LINEAR[b];
}

/** Counts WCAG transitions (half-flashes) on one luminance signal, with timestamps in ms. */
export class FlashTracker {
  constructor(value = 0) {
    this.lo = this.hi = value;
    this.direction = 0;
    this.marks = [];
  }

  flip(v) {
    const hi = Math.max(this.hi, v);
    const lo = Math.min(this.lo, v);
    if (this.direction >= 0 && hi - v >= FLASH_DELTA && v < DARK_BELOW) return -1;
    if (this.direction <= 0 && v - lo >= FLASH_DELTA && lo < DARK_BELOW) return 1;
    return 0;
  }

  recent(now) {
    while (this.marks.length && this.marks[0] <= now - 1000) this.marks.shift();
    return this.marks.length;
  }

  allows(v, now, perSecond) {
    return this.flip(v) === 0 || this.recent(now) < 2 * perSecond;
  }

  commit(v, now) {
    const flip = this.flip(v);
    this.hi = Math.max(this.hi, v);
    this.lo = Math.min(this.lo, v);
    if (flip !== 0) {
      this.marks.push(now);
      this.direction = flip;
      this.hi = this.lo = v;
    }
    return this.recent(now);
  }
}

const facadeLuminance = (grid) => {
  let sum = 0;
  let n = 0;
  for (const row of grid) for (const px of row) (sum += luminance(px)), n++;
  return sum / n;
};

export class FlashGuard {
  constructor({ perSecond = GUARD_FLASHES_PER_SECOND } = {}) {
    this.perSecond = perSecond;
    this.shown = null;
    this.lastAt = null;
    this.trackers = null;
    this.facade = null;
  }

  /** Returns the grid that is safe to show at time `now` (ms). Frame spacing may vary. */
  filter(grid, now) {
    if (!this.shown) {
      this.shown = grid.map((row) => row.map((px) => [...px]));
      this.trackers = grid.map((row) => row.map((px) => new FlashTracker(luminance(px))));
      this.facade = new FlashTracker(facadeLuminance(grid));
      this.lastAt = now;
      return this.shown;
    }
    const dt = Math.max(1, now - this.lastAt);
    this.lastAt = now;
    const step = Math.max(1, Math.round((255 / (RAMP_SECONDS * REFERENCE_FPS)) * (dt / (1000 / REFERENCE_FPS))));

    const out = grid.map((row, r) =>
      row.map((want, c) => {
        const prev = this.shown[r][c];
        let next = prev.map((p, i) => p + Math.max(-step, Math.min(step, want[i] - p)));
        const tracker = this.trackers[r][c];
        if (!tracker.allows(luminance(next), now, this.perSecond)) next = prev;
        tracker.commit(luminance(next), now);
        return next;
      }),
    );

    let shown = out;
    if (!this.facade.allows(facadeLuminance(out), now, this.perSecond)) {
      shown = this.shown; // the whole facade would flash: hold the last frame
      shown.forEach((row, r) => row.forEach((px, c) => this.trackers[r][c].commit(luminance(px), now)));
    }
    this.facade.commit(facadeLuminance(shown), now);
    this.shown = shown;
    return shown;
  }
}

/** Worst flashes-per-second in any 1 s window: { rate, where } (where = "r,c" or "facade"). */
export function worstFlashRate(frames, fps) {
  const trackers = new Map();
  let worst = { rate: 0, where: null };
  frames.forEach((grid, i) => {
    const now = (i * 1000) / fps;
    const values = [["facade", facadeLuminance(grid)]];
    grid.forEach((row, r) => row.forEach((px, c) => values.push([`${r},${c}`, luminance(px)])));
    for (const [where, v] of values) {
      if (!trackers.has(where)) trackers.set(where, new FlashTracker(v));
      const rate = trackers.get(where).commit(v, now) / 2;
      if (rate > worst.rate) worst = { rate, where };
    }
  });
  return worst;
}
