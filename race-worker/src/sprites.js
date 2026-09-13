// Pixel art for the Green Building: one char = one window, "." = leave the window alone.
//
// Each mascot is a single 9x9 drawing; every pose is derived from it:
//   E  eye           (closes to `lid` on blink / sleep)
//   M  mouth / beak  (shows `closed` normally, red when eating)
// Minis are 2x3 versions that fit one 3-row race lane.

const WHITE = [205, 205, 205]; // full 255 white blooms into a blob on the lit facade

const COMMON = {
  R: [255, 30, 30], // open mouth
  D: [70, 35, 10], // closed eye line
  T: [190, 190, 180], // teeth
  N: [255, 80, 120], // nose
  Y: [255, 190, 0], // beak / feet
};

function mascot({ name, school, sprite, mini, palette, eye = WHITE, lid = "B", closed = "L" }) {
  const colors = { ...COMMON, ...palette, E: eye, M: palette[closed] };
  const swap = (rows, from, to) => rows.map((row) => row.replaceAll(from, to));
  const poses = {
    idle: sprite,
    blink: swap(sprite, "E", lid),
    eat: swap(sprite, "M", "R"),
    sleep: swap(swap(sprite, "E", "D"), "M", closed),
  };
  return { name, school, sprite, mini, colors, poses };
}

export const MASCOTS = {
  beaver: mascot({
    name: "Tim the Beaver",
    school: "mit",
    sprite: [".B.....B.", ".BBBBBBB.", "BBEBBBEBB", "BBBLNLBBB", ".BBTMTBB.", "..BBBBB..", ".BLLLLLB.", ".BLLLLLBK", ".BB...BBK"],
    mini: ["BB", "EE", "LL"],
    palette: { B: [185, 105, 35], L: [235, 170, 100], K: [110, 55, 15] },
  }),
  pilgrim: mascot({
    name: "John Harvard",
    school: "harvard",
    sprite: ["..HHHHH..", "..HHYHH..", "HHHHHHHHH", ".GLLLLLG.", ".GELLLEG.", ".GLLMLLG.", "..CCCCC..", ".KKKKKKK.", ".KK...KK."],
    mini: ["HH", "LL", "KK"],
    palette: { H: [90, 90, 140], G: [150, 150, 165], L: [230, 170, 130], C: [200, 200, 190], K: [190, 30, 55] },
    eye: [80, 40, 20],
    lid: "L",
  }),
  terrier: mascot({
    name: "Rhett the Terrier",
    school: "bu",
    sprite: ["BB.....BB", "BBB...BBB", "BBBBLBBBB", "BEBBLBBEB", "BBLLNLLBB", ".BLLMLLB.", "..KKKKK..", ".BBLLLBB.", ".BB...BB."],
    mini: ["BB", "LL", "KK"],
    palette: { B: [80, 95, 200], L: [190, 190, 190], K: [204, 0, 0] },
  }),
  husky: mascot({
    name: "Paws the Husky",
    school: "neu",
    sprite: ["B.......B", "BB.....BB", "BBBBBBBBB", "BLELLLELB", "BLLLNLLLB", ".LLLMLLL.", "..BLLLB..", ".BBLLLBB.", ".BB...BB."],
    mini: ["BB", "EE", "LL"],
    palette: { B: [120, 130, 150], L: [185, 190, 200] },
    eye: [90, 190, 255],
    lid: "L",
  }),
  duck: mascot({
    name: "The Duck King",
    school: null,
    sprite: ["...BBB...", "..BBBBB..", "..BEBBYY.", "..BBBBM..", "...BBB...", ".BBBBBBB.", "BBBBBBBB.", ".BBBBBB..", "..Y..Y..."],
    mini: ["BB", "BY", "BB"],
    palette: { B: [200, 160, 10], Y: [255, 90, 0] },
    eye: [40, 30, 0],
    closed: "Y",
  }),
};

export const MASCOT_FOR_SCHOOL = Object.fromEntries(
  Object.entries(MASCOTS)
    .filter(([, m]) => m.school)
    .map(([id, m]) => [m.school, id]),
);

export const GOLD = [210, 160, 20];
export const CROWN = { sprite: ["Y.Y.Y", "YYRYY"], colors: { Y: GOLD, R: [200, 20, 40] } };

// 3x5 digits for the countdown (same glyphs as the Python font).
export const DIGITS = {
  1: [".#.", "##.", ".#.", ".#.", "###"],
  2: ["###", "..#", "###", "#..", "###"],
  3: ["###", "..#", "###", "..#", "###"],
};

export function blank(rows, cols, fill) {
  return Array.from({ length: rows }, () => Array.from({ length: cols }, () => fill));
}

/** Draw `sprite` with its top-left at (top, left); off-grid pixels are clipped. */
export function blit(grid, sprite, top, left, colors, alpha = 1) {
  sprite.forEach((line, r) => {
    [...line].forEach((ch, c) => {
      const color = colors[ch];
      const row = grid[top + r];
      if (!color || !row || left + c < 0 || left + c >= row.length) return;
      row[left + c] = alpha >= 1 ? color : mix(row[left + c], color, alpha);
    });
  });
}

export function mix(a, b, t) {
  return a.map((v, i) => Math.round(v + (b[i] - v) * t));
}

export function scale(color, k) {
  return color.map((v) => Math.max(0, Math.min(255, Math.round(v * k))));
}

/** Put a school's mini mascot at the head of its lane (`progressCols` 0..8). */
export function drawLaneMascot(grid, school, laneTop, progressCols, alpha = 1) {
  const m = MASCOTS[MASCOT_FOR_SCHOOL[school]];
  if (!m) return;
  const left = Math.max(0, Math.min(grid[0].length - 2, Math.round(progressCols)));
  blit(grid, m.mini, laneTop, left, m.colors, alpha);
}
