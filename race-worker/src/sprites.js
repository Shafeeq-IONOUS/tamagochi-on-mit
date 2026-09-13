// Pixel art for the Green Building: one char = one window, "." = leave the window alone.
//
// Each mascot is a single 9x9 drawing; every pose is derived from it:
//   E  eye           (closes to `lid` on blink / sleep)
//   M  mouth / beak  (shows `closed` normally, red when eating)
// Minis are 2x3 versions that fit one 3-row race lane.
//
// `sprite5` is a hand-designed 5x5 reinterpretation of the same character (not an algorithmic
// downscale of `sprite` — 25 pixels is too few for that to read at all). Each one leans on the
// single most identifying feature of the mascot (the beaver's front teeth + tail, the pilgrim's
// broad hat brim, the terrier's red collar, the husky's blue eyes, the duck's bill) and reuses
// the mascot's own `palette`/`eye`/`lid`/`closed` so the colors stay the same character, just
// simplified — see each mascot below for which color regions got merged or dropped to fit.
//
// No baby/head_rows crop for sprite5: that concept belonged to the original Python prototype
// (removed from this repo; see tamagochi-mascots-python/ in earlier history) and never carried
// over to this JS port, which only ever derives idle/blink/eat/sleep poses. 5x5 is already at
// the floor of legibility, so there's no room left to crop further for a "baby" stage — adult-
// only is the only sane choice here.

const WHITE = [205, 205, 205]; // full 255 white blooms into a blob on the lit facade

const COMMON = {
  R: [255, 30, 30], // open mouth
  D: [70, 35, 10], // closed eye line
  T: [190, 190, 180], // teeth
  N: [255, 80, 120], // nose
  Y: [255, 190, 0], // beak / feet
};

function mascot({ name, school, sprite, sprite5, mini, palette, eye = WHITE, lid = "B", closed = "L" }) {
  const colors = { ...COMMON, ...palette, E: eye, M: palette[closed] };
  const swap = (rows, from, to) => rows.map((row) => row.replaceAll(from, to));
  const posesOf = (base) => ({
    idle: base,
    blink: swap(base, "E", lid),
    eat: swap(base, "M", "R"),
    sleep: swap(swap(base, "E", "D"), "M", closed),
  });
  return { name, school, sprite, sprite5, mini, colors, poses: posesOf(sprite), poses5: sprite5 && posesOf(sprite5) };
}

export const MASCOTS = {
  beaver: mascot({
    name: "Tim the Beaver",
    school: "mit",
    sprite: [".B.....B.", ".BBBBBBB.", "BBEBBBEBB", "BBBLNLBBB", ".BBTMTBB.", "..BBBBB..", ".BLLLLLB.", ".BLLLLLBK", ".BB...BBK"],
    // 5x5: round brown head, buck teeth (T/M) front and center, flat dark tail nub (K) below —
    // teeth + tail are Tim's two signature features, so both survive the cut. L (belly/light fur)
    // isn't needed at this size and is dropped; closed mouth falls back to the default "L" so it
    // reads as bare skin between the teeth, same idea as the 9x9.
    sprite5: [".BBB.", "BEBEB", ".TMT.", "BBBBB", ".KKK."],
    mini: ["BB", "EE", "LL"],
    palette: { B: [185, 105, 35], L: [235, 170, 100], K: [110, 55, 15] },
  }),
  pilgrim: mascot({
    name: "John Harvard",
    school: "harvard",
    sprite: ["..HHHHH..", "..HHYHH..", "HHHHHHHHH", ".GLLLLLG.", ".GELLLEG.", ".GLLMLLG.", "..CCCCC..", ".KKKKKKK.", ".KK...KK."],
    // 5x5: the broad hat brim (row 2, wider than the crown above it) is the single most
    // identifying shape here, plus the white collar over the crimson robe. G (hat side shading)
    // and Y (buckle) are dropped for lack of room; H/L/C/K keep the same colors as the 9x9.
    // Face row: both eyes at the outer edges flanking a centred mouth (was missing an eye).
    sprite5: [".HHH.", "HHHHH", "ELMLE", "CCCCC", "KKKKK"],
    mini: ["HH", "LL", "KK"],
    palette: { H: [90, 90, 140], G: [150, 150, 165], L: [230, 170, 130], C: [200, 200, 190], K: [190, 30, 55] },
    eye: [80, 40, 20],
    lid: "L",
  }),
  terrier: mascot({
    name: "Rhett the Terrier",
    school: "bu",
    sprite: ["BB.....BB", "BBB...BBB", "BBBBLBBBB", "BEBBLBBEB", "BBLLNLLBB", ".BLLMLLB.", "..KKKKK..", ".BBLLLBB.", ".BB...BB."],
    // 5x5: perked/floppy ears at the top corners and a solid red collar band (K) across the
    // bottom are Rhett's tells — the collar in particular is BU red, unmistakable even at this
    // size. Same B/L/K colors as the 9x9, no new palette entries needed.
    sprite5: ["B...B", "BBBBB", "EBLBE", ".LML.", ".KKK."],
    mini: ["BB", "LL", "KK"],
    palette: { B: [80, 95, 200], L: [190, 190, 190], K: [204, 0, 0] },
    eye: [25, 22, 20], // black, not the default light eye
  }),
  husky: mascot({
    name: "Paws the Husky",
    school: "neu",
    sprite: ["B.......B", "BB.....BB", "BBBBBBBBB", "BLELLLELB", "BLLLNLLLB", ".LLLMLLL.", "..BLLLB..", ".BBLLLBB.", ".BB...BB."],
    // 5x5: sharp pointed ears at the top corners plus the pale-blue eyes (from `eye`, unchanged)
    // front and center — pointed ears + blue eyes are Paws' whole identity. Same B/L colors as
    // the 9x9.
    sprite5: ["B...B", "BBBBB", "LELEL", ".LML.", ".BBB."],
    mini: ["BB", "EE", "LL"],
    palette: { B: [120, 130, 150], L: [185, 190, 200] },
    eye: [90, 190, 255],
    lid: "L",
  }),
  duck: mascot({
    name: "The Duck King",
    school: null,
    sprite: ["...BBB...", "..BBBBB..", "..BEBBYY.", "..BBBBM..", "...BBB...", ".BBBBBBB.", "BBBBBBBB.", ".BBBBBB..", "..Y..Y..."],
    // 5x5: a two-pixel orange bill (Y/M) jutting off the round golden head is the one shape that
    // reads as "duck" rather than "generic bird", plus two webbed feet (Y) peeking out below.
    // Same B/Y colors and `closed: "Y"` as the 9x9, so the bill tip stays orange until eating.
    sprite5: [".BBB.", "BEBYM", ".BBB.", "BBBBB", ".Y.Y."],
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

/** Draw a school's 2x3 mini mascot with its top-left at (top, left); clipped off-grid. */
export function drawLaneMascot(grid, school, left, top, alpha = 1) {
  const m = MASCOTS[MASCOT_FOR_SCHOOL[school]];
  if (m) blit(grid, m.mini, top, left, m.colors, alpha);
}
