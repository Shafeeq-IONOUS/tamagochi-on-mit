// The show as a list of frames, for tests and the preview script.
import { DEFAULT_SCENE_CONFIG, frameFor } from "../src/scenes.js";
import { FINISH_COLUMNS } from "../src/render.js";
import { SCHOOLS } from "../src/mascots.js";

// Relative climbing speed per school in the demo race (SCHOOLS order).
const DEMO_SPEEDS = [1, 0.85, 0.7, 0.9];

/**
 * reign (reignSeconds) -> intro -> countdown -> race, sampled at `fps`.
 * With `raceSeconds` the race is a demo climb that ends when the fastest lane reaches the top,
 * followed by 3 s of the finished frame; otherwise it is 1 s of the race's first frame.
 */
export function showSequence({ champion = null, fps = 15, reignSeconds = 4, config = DEFAULT_SCENE_CONFIG, raceSeconds = 0 } = {}) {
  const frames = [];
  const sample = (status, seconds, extra = () => ({}), phaseStartedAt = 0) => {
    for (let i = 0; i < Math.round(seconds * fps); i++) {
      const t = (i * 1000) / fps;
      frames.push(frameFor({ status, champion, config, phaseStartedAt, winner: null, ...zeroProgress(), ...extra(t) }, phaseStartedAt + t));
    }
  };

  sample("idle", reignSeconds, () => ({}), 0);
  sample("intro", config.introSeconds);
  sample("countdown", config.countdownSeconds);
  if (!raceSeconds) {
    sample("running", 1);
    return frames;
  }
  const progressAt = (t) =>
    Object.fromEntries(SCHOOLS.map((s, i) => [s, Math.min(FINISH_COLUMNS, (DEMO_SPEEDS[i] * t * FINISH_COLUMNS) / (raceSeconds * 1000))]));
  sample("running", raceSeconds, (t) => ({ progressCols: progressAt(t) }));
  const final = progressAt(raceSeconds * 1000);
  const winner = SCHOOLS[DEMO_SPEEDS.indexOf(Math.max(...DEMO_SPEEDS))];
  sample("finished", 3, () => ({ status: "finished", progressCols: final, winner }));
  return frames;
}

const zeroProgress = () => ({ progressCols: Object.fromEntries(SCHOOLS.map((s) => [s, 0])) });
