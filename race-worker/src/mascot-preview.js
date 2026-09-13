// A single static frame per mascot, centred on the 17x9 facade — a quick way for the host
// to eyeball each character's colours/shape on the real display before the event.
//
// Kept as its own tiny pure module (rather than inline in race-state.js) so it can be unit
// tested with plain `node --test`: race-state.js imports `cloudflare:workers`, which only
// resolves inside the Workers runtime, so nothing that file imports gets exercised by the
// existing node test suite.
import { COLS, OFF, ROWS } from "./render.js";
import { MASCOTS, blank, blit } from "./sprites.js";

/** 17x9 grid with `id`'s idle pose centred on the facade. `size` picks the 9x9 sprite (the
 * default) or the 5x5 one (`sprite5`/`poses5` in sprites.js). Throws for an unknown id, or
 * for a mascot with no 5x5 art if `size` is 5. */
export function centeredMascotFrame(id, size = 9) {
  const mascot = MASCOTS[id];
  if (!mascot) throw new Error(`unknown mascot: ${id}`);
  const poses = size === 5 ? mascot.poses5 : mascot.poses;
  if (!poses) throw new Error(`${id} has no ${size}x${size} art`);
  const sprite = poses.idle;
  const grid = blank(ROWS, COLS, OFF);
  const top = Math.floor((ROWS - sprite.length) / 2);
  const left = Math.floor((COLS - sprite[0].length) / 2);
  blit(grid, sprite, top, left, mascot.colors);
  return grid;
}
