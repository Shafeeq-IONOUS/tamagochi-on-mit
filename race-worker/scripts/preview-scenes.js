// Play the pre-race show (reign -> intro -> countdown -> race start) without deploying.
//
//   node scripts/preview-scenes.js --instance <name> [--champion mit] [--loop]
//   node scripts/preview-scenes.js --clips <dir>          # .bin clips in the sim's demo format
//
// Posting frames to an instance needs only its name, not the event password. Use your own
// instance, not the shared production one.
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";

import { packFrame } from "../src/render.js";
import { FlashGuard } from "../src/safety.js";
import { showSequence } from "./sequence.js";

const FPS = 15;
const SIM_BASE = "https://sundai.willsarg.com";

const { values: args } = parseArgs({
  options: {
    instance: { type: "string" },
    champion: { type: "string" },
    clips: { type: "string" },
    loop: { type: "boolean", default: false },
  },
});

function guarded(frames) {
  const guard = new FlashGuard();
  return frames.map((grid, i) => guard.filter(grid, (i * 1000) / FPS));
}

/** Simulator clip format: "C", fps, frame count (uint16 LE), then 459 RGB bytes per frame. */
function clipBytes(frames) {
  const header = Uint8Array.of(67, FPS, frames.length & 0xff, frames.length >> 8);
  return Buffer.concat([header, ...frames.map((grid) => packFrame(grid))]);
}

const champions = args.champion ? [args.champion] : [null, "mit", "harvard", "bu", "neu"];

if (args.clips) {
  mkdirSync(args.clips, { recursive: true });
  for (const champion of champions) {
    const path = join(args.clips, `scenes-${champion ?? "duck"}.bin`);
    writeFileSync(path, clipBytes(guarded(showSequence({ champion, fps: FPS }))));
    console.log(`wrote ${path}`);
  }
}

if (args.instance) {
  const url = `${SIM_BASE}/api/i/${args.instance}/frame`;
  console.log(`playing on ${url} — watch ${SIM_BASE}/${args.instance}`);
  do {
    for (const champion of champions) {
      console.log(`king: ${champion ?? "the Duck King"}`);
      for (const grid of guarded(showSequence({ champion, fps: FPS }))) {
        const started = Date.now();
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/octet-stream", "User-Agent": "race-worker-preview/1" },
          body: packFrame(grid),
        });
        if (!resp.ok) throw new Error(`sim rejected frame: HTTP ${resp.status} ${await resp.text()}`);
        await new Promise((resolve) => setTimeout(resolve, Math.max(0, 1000 / FPS - (Date.now() - started))));
      }
    }
  } while (args.loop);
}

if (!args.instance && !args.clips) {
  console.log("usage: node scripts/preview-scenes.js --instance <name> [--champion mit] [--loop] | --clips <dir>");
}
