"""The shared pet: vital stats, life stages, and what each crowd action does.

Everything here is pure state; rendering lives in render.py and networking in server.py.
"""

import threading
import time
from collections import deque, Counter

STAT_NAMES = ("hunger", "happy", "energy", "clean")

# Points drained per minute. Tuned so an untended pet looks miserable after ~20 minutes.
DECAY_PER_MIN = {"hunger": 4.0, "happy": 3.0, "energy": 2.0, "clean": 2.5}

ACTIONS = {
    #          stat changes                          care points
    "feed":  ({"hunger": +12, "clean": -2},           1),
    "play":  ({"happy": +10, "energy": -4, "hunger": -2}, 1),
    "pet":   ({"happy": +5},                          1),
    "clean": ({"clean": +20},                         1),
    "sleep": ({"energy": +15},                        1),
    "cheer": ({},                                     1),  # pure hype, feeds the crowd meter
}

HATCH_AT = 50       # taps the crowd needs to hatch the egg
ADULT_AT = 1500     # care points to grow up
CROWD_WINDOW = 10   # seconds used for the "hype" meter
SCHOOL_WINDOW = 300 # seconds used for the school leaderboard


class Pet:
    def __init__(self):
        self.lock = threading.Lock()
        self.stats = {k: 70.0 for k in STAT_NAMES}
        self.care = 0
        self.born = None  # set when the egg hatches
        self.last_tick = time.time()
        self.recent = deque()  # (timestamp, action, school)
        self.totals = Counter()  # all-time actions per school
        self.events = deque(maxlen=64)  # for the renderer: (timestamp, action, school)

    # ---- life stage -------------------------------------------------------

    @property
    def stage(self):
        if self.born is None:
            return "egg"
        return "adult" if self.care >= ADULT_AT else "baby"

    @property
    def mood(self):
        s = self.stats
        if s["energy"] < 15:
            return "sleepy"
        if s["hunger"] < 20:
            return "hungry"
        if s["clean"] < 20:
            return "dirty"
        if s["happy"] < 25:
            return "sad"
        if min(s.values()) > 70:
            return "ecstatic"
        return "ok"

    # ---- updates ----------------------------------------------------------

    def tick(self, now=None):
        now = now or time.time()
        with self.lock:
            dt_min = (now - self.last_tick) / 60
            self.last_tick = now
            if self.born is not None:
                for k, rate in DECAY_PER_MIN.items():
                    self.stats[k] = max(0.0, self.stats[k] - rate * dt_min)
            while self.recent and now - self.recent[0][0] > SCHOOL_WINDOW:
                self.recent.popleft()

    def act(self, action, school, now=None):
        if action not in ACTIONS:
            raise ValueError(f"unknown action {action!r}")
        now = now or time.time()
        with self.lock:
            changes, points = ACTIONS[action]
            if self.born is None:
                self.care += points  # every tap warms the egg
                if self.care >= HATCH_AT:
                    self.born = now
                    self.events.append((now, "hatch", school))
            else:
                for k, dv in changes.items():
                    self.stats[k] = max(0.0, min(100.0, self.stats[k] + dv))
                self.care += points
            self.recent.append((now, action, school))
            self.totals[school] += 1
            self.events.append((now, action, school))

    # ---- crowd metrics ----------------------------------------------------

    def hype(self, now=None):
        """Actions per second over the last few seconds (0 = nobody, 3+ = party)."""
        now = now or time.time()
        n = sum(1 for ts, _, _ in self.recent if now - ts <= CROWD_WINDOW)
        return n / CROWD_WINDOW

    def leaderboard(self):
        return Counter(school for _, _, school in self.recent).most_common()

    def snapshot(self, now=None):
        with self.lock:
            return {
                "stage": self.stage,
                "mood": self.mood,
                "stats": {k: round(v) for k, v in self.stats.items()},
                "care": self.care,
                "hatch_at": HATCH_AT,
                "adult_at": ADULT_AT,
                "hype": round(self.hype(now), 2),
                "leaderboard": self.leaderboard()[:9],
                "totals": self.totals.most_common(),
            }
