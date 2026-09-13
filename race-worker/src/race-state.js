import { DurableObject } from "cloudflare:workers";
import { SCHOOLS, isSchool } from "./mascots.js";
import { packFrame, FINISH_COLUMNS } from "./render.js";
import { ANIMATED_STATUSES, DEFAULT_SCENE_CONFIG, frameFor, validateSceneConfig } from "./scenes.js";
import { FlashGuard } from "./safety.js";

const CHEERS_PER_COLUMN = 12; // crowd-tunable: lower = faster race
const ALARM_INTERVAL_MS = 400; // how often a running race repaints the building
const CHEER_COOLDOWN_MS = 150; // per (ip, school) — blocks scripts, not enthusiastic tapping
const SIM_BASE = "https://sundai.willsarg.com";

// Scenes (reign / intro / countdown) need smoother motion than the race's 400 ms repaint.
// One alarm invocation streams a short batch of frames, then re-arms; a batch stays under
// the Workers free-plan limit of 50 subrequests per invocation.
const SCENE_FPS = 15;
const REIGN_FPS = 8;
const BATCH_MS = 2800;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const DEFAULT_STATE = () => ({
  status: "idle", // idle (reign) | intro | countdown | running | finished
  cheers: Object.fromEntries(SCHOOLS.map((s) => [s, 0])),
  startedAt: null,
  finishedAt: null,
  winner: null,
  phaseStartedAt: Date.now(),
  phaseEndsAt: null,
  champion: null, // school wearing the crown; null = the Duck King
  config: { ...DEFAULT_SCENE_CONFIG },
  instance: null, // sim instance name; set via env default or admin rotateInstance()
});

export class RaceState extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.env = env;
    this.lastCheerAt = new Map();
    this.guard = new FlashGuard();
    this.state_ = null;
    ctx.blockConcurrencyWhile(async () => {
      const stored = await ctx.storage.get("state");
      this.state_ = { ...DEFAULT_STATE(), ...stored };
      if (!this.state_.instance && env.SIM_INSTANCE) this.state_.instance = env.SIM_INSTANCE;
      // keep the reign / intro animating after a restart or deploy
      if (ANIMATED_STATUSES.includes(this.state_.status) && !(await ctx.storage.getAlarm())) {
        await ctx.storage.setAlarm(Date.now());
      }
    });
  }

  async persist() {
    await this.ctx.storage.put("state", this.state_);
  }

  progressCols() {
    const out = {};
    for (const school of SCHOOLS) {
      out[school] = Math.min(FINISH_COLUMNS, this.state_.cheers[school] / CHEERS_PER_COLUMN);
    }
    return out;
  }

  publicState() {
    return {
      status: this.state_.status,
      cheers: this.state_.cheers,
      progressCols: this.progressCols(),
      startedAt: this.state_.startedAt,
      finishedAt: this.state_.finishedAt,
      winner: this.state_.winner,
      phaseStartedAt: this.state_.phaseStartedAt,
      phaseEndsAt: this.state_.phaseEndsAt,
      serverTime: Date.now(),
      champion: this.state_.champion,
      config: this.state_.config,
      hasInstance: Boolean(this.state_.instance),
    };
  }

  enterPhase(status, now, seconds = null) {
    this.state_.status = status;
    this.state_.phaseStartedAt = now;
    this.state_.phaseEndsAt = seconds === null ? null : now + seconds * 1000;
  }

  /** Move intro -> countdown -> running once their time is up. */
  async advance(now) {
    const { status, phaseEndsAt, config } = this.state_;
    if (!phaseEndsAt || now < phaseEndsAt) return;
    if (status === "intro" && config.countdownSeconds > 0) {
      this.enterPhase("countdown", phaseEndsAt, config.countdownSeconds);
    } else if (status === "intro" || status === "countdown") {
      this.enterPhase("running", phaseEndsAt);
      this.state_.startedAt = phaseEndsAt;
    } else {
      return;
    }
    await this.persist();
    await this.advance(now); // a long stall may skip a whole phase
  }

  // -- public RPCs (called from the Worker's fetch router) -------------------

  async getState() {
    await this.advance(Date.now());
    return this.publicState();
  }

  async cheer(school, ip) {
    if (!isSchool(school)) throw new Error("unknown school");
    await this.advance(Date.now());
    if (this.state_.status !== "running") return { ok: false, reason: "not running", state: this.publicState() };

    const key = `${ip}|${school}`;
    const now = Date.now();
    const last = this.lastCheerAt.get(key) ?? 0;
    if (now - last < CHEER_COOLDOWN_MS) {
      return { ok: false, reason: "cooldown", state: this.publicState() };
    }
    this.lastCheerAt.set(key, now);

    this.state_.cheers[school] += 1;
    await this.checkWin();
    await this.persist();
    return { ok: true, state: this.publicState() };
  }

  async checkWin() {
    if (this.state_.status !== "running") return;
    const progress = this.progressCols();
    const winner = SCHOOLS.find((s) => progress[s] >= FINISH_COLUMNS);
    if (winner) {
      this.enterPhase("finished", Date.now());
      this.state_.winner = winner;
      this.state_.champion = winner; // reigns until the next race's intro
      this.state_.finishedAt = Date.now();
      await this.ctx.storage.deleteAlarm();
      await this.pushFrame();
    }
  }

  /** Host pressed Start: the reigning king abdicates (intro), countdown, then the race. */
  async start() {
    const now = Date.now();
    const { instance, champion, config } = this.state_;
    this.state_ = { ...DEFAULT_STATE(), instance, champion, config };
    this.enterPhase("intro", now, config.introSeconds);
    await this.persist();
    await this.ctx.storage.setAlarm(now); // paint immediately, alarm() reschedules
    return this.publicState();
  }

  /** Back to the reign: pauses a race in progress, or ends the winner announcement. */
  async stop() {
    if (this.state_.status !== "idle") this.enterPhase("idle", Date.now());
    await this.persist();
    await this.ctx.storage.setAlarm(Date.now());
    return this.publicState();
  }

  /** Full wipe: no race, and the Duck King gets the crown back. Host timing config is kept. */
  async reset() {
    this.state_ = { ...DEFAULT_STATE(), instance: this.state_.instance, config: this.state_.config };
    await this.persist();
    await this.ctx.storage.setAlarm(Date.now());
    return this.publicState();
  }

  async setConfig(input) {
    this.state_.config = validateSceneConfig(input, this.state_.config);
    await this.persist();
    return this.publicState();
  }

  /** Mint a fresh sim instance with the event password and adopt it. Admin-only, used if
   * the current instance ever gets reset/expired. The password never leaves the Worker. */
  async rotateInstance() {
    if (!this.env.SIM_PASSWORD) throw new Error("SIM_PASSWORD not configured");
    const resp = await fetch(`${SIM_BASE}/api/instances`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "User-Agent": "race-worker/1" },
      body: JSON.stringify({ password: this.env.SIM_PASSWORD }),
    });
    if (!resp.ok) throw new Error(`instance mint failed: HTTP ${resp.status}`);
    const data = await resp.json();
    this.state_.instance = data.name;
    await this.persist();
    return { name: data.name, view_url: data.view_url };
  }

  async pushFrame(now = Date.now()) {
    if (!this.state_.instance) return;
    const state = { ...this.state_, progressCols: this.progressCols() };
    const body = packFrame(this.guard.filter(frameFor(state, now), now));
    try {
      await fetch(`${SIM_BASE}/api/i/${this.state_.instance}/frame`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream", "User-Agent": "race-worker/1" },
        body,
      });
    } catch {
      // best-effort — a dropped frame just means the display is a beat behind, never fatal
    }
  }

  async alarm() {
    if (!this.state_.instance) return;
    const batchStart = Date.now();
    while (ANIMATED_STATUSES.includes(this.state_.status) && Date.now() - batchStart < BATCH_MS) {
      const now = Date.now();
      await this.advance(now);
      if (!ANIMATED_STATUSES.includes(this.state_.status)) break;
      await this.pushFrame(now);
      const fps = this.state_.status === "idle" ? REIGN_FPS : SCENE_FPS;
      await sleep(Math.max(0, 1000 / fps - (Date.now() - now)));
    }

    if (ANIMATED_STATUSES.includes(this.state_.status)) {
      await this.ctx.storage.setAlarm(Date.now());
    } else if (this.state_.status === "running") {
      await this.pushFrame();
      await this.checkWin();
      if (this.state_.status === "running") {
        await this.ctx.storage.setAlarm(Date.now() + ALARM_INTERVAL_MS);
      }
    }
  }
}
