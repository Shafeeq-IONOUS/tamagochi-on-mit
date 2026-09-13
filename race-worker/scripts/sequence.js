// The pre-race show as a list of frames, for tests and the preview script.
import { DEFAULT_SCENE_CONFIG, frameFor } from "../src/scenes.js";
import { SCHOOLS } from "../src/mascots.js";

/** reign (reignSeconds) -> intro -> countdown -> race start (1 s), sampled at `fps`. */
export function showSequence({ champion = null, fps = 15, reignSeconds = 4, config = DEFAULT_SCENE_CONFIG } = {}) {
  const progressCols = Object.fromEntries(SCHOOLS.map((s) => [s, 0]));
  const phases = [
    ["idle", reignSeconds],
    ["intro", config.introSeconds],
    ["countdown", config.countdownSeconds],
    ["running", 1],
  ];
  const frames = [];
  let phaseStartedAt = 0;
  for (const [status, seconds] of phases) {
    const n = Math.round(seconds * fps);
    for (let i = 0; i < n; i++) {
      const now = phaseStartedAt + (i * 1000) / fps;
      frames.push(frameFor({ status, champion, config, phaseStartedAt, progressCols, winner: null }, now));
    }
    phaseStartedAt += seconds * 1000;
  }
  return frames;
}
