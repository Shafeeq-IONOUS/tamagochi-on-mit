"""Turns pet state into 17 x 9 frames.

Floor layout (row 0 = top floor):
   0      school banner - flashes the colour of whoever just interacted
   1-11   sky + pet (particles travel up and down these floors)
   12     ground (poop piles up here when the pet is dirty)
   13-16  stat bars: hunger, happy, energy, clean
"""

import math
import time

from tower.display import COLS, ROWS, WHITE, Frame, mix, scale
from tower.font import draw_number, draw_scroll
from tamagotchi import mascots, schools, sprites
from tamagotchi.pet import STAT_NAMES

BANNER_ROW = 0
GROUND_ROW = 12
BAR_TOP = 13
STAT_COLORS = {
    "hunger": (255, 140, 0),
    "happy": (255, 60, 160),
    "energy": (255, 230, 0),
    "clean": (0, 220, 255),
}
PARTY_HYPE = 1.5         # actions/second that make the mascot bounce
LEADERBOARD_EVERY = 120  # seconds between leaderboard takeovers
LEADERBOARD_FOR = 8
HATCH_SHOW_FOR = 5
NIGHT_HOURS = range(1, 7)


def _seed(ts):
    """Stable pseudo-random column for an event, from its timestamp."""
    return int(ts * 1000) % 7919


class Renderer:
    def __init__(self, pet, start=None, leaderboard_every=LEADERBOARD_EVERY, mascot="auto"):
        self.pet = pet
        self.mascot = mascot
        self.start = start or time.time()
        self.leaderboard_every = leaderboard_every
        self.mouth_row = 7

    def render(self, now=None):
        now = now or time.time()
        snap = self.pet.snapshot(now)
        events = [e for e in list(self.pet.events) if now - e[0] < HATCH_SHOW_FOR]
        f = Frame()

        hatch = next((e for e in events if e[1] == "hatch"), None)
        events = [e for e in events if now - e[0] < 3.0]
        if hatch:
            self._hatch_show(f, now - hatch[0])
            return f

        t = now - self.start
        every = self.leaderboard_every
        if snap["leaderboard"] and t > every and t % every < LEADERBOARD_FOR:
            self._leaderboard(f, snap, t % every)
            return f

        party = snap["hype"] >= PARTY_HYPE
        self._banner(f, events, now, t)
        if snap["stage"] == "egg":
            self._egg(f, snap, events, now)
        else:
            self._pet(f, snap, events, now, t, party)
            self._ground(f, snap, t)
            self._bars(f, snap, t)
            self._particles(f, events, now, snap["stage"])
        if time.localtime(now).tm_hour in NIGHT_HOURS:
            self._dim(f, 0.45)
        return f

    # ---- layers -----------------------------------------------------------

    def _banner(self, f, events, now, t):
        # Steady, dim colour of whoever acted last. Never flashes: rapid taps from different
        # schools would otherwise strobe the top floor.
        school = events[-1][2] if events else "mit"
        f.fill_row(BANNER_ROW, scale(schools.color(school), 0.3))

    def _egg(self, f, snap, events, now):
        progress = snap["care"] / snap["hatch_at"]
        wobble = 0
        if events and now - events[-1][0] < 0.4:
            wobble = 1 if (now - events[-1][0]) < 0.2 else -1
        top, left = 5, 2 + wobble
        f.blit(sprites.EGG, top, left, sprites.EGG_PALETTE)
        cracks = int(progress * len(sprites.EGG_CRACKS))
        for r, c in sprites.EGG_CRACKS[:cracks]:
            f.set(top + r, left + c, sprites.EGG_PALETTE["C"])
        # "Warmth" fills the tower from the bottom as the crowd taps.
        lit_rows = int(progress * (ROWS - GROUND_ROW))
        for i in range(lit_rows):
            f.fill_row(ROWS - 1 - i, scale((255, 120, 0), 0.25 + 0.15 * math.sin(now * 4 + i)))
        f.fill_row(GROUND_ROW, (0, 60, 0))
        draw_scroll(f, f"TAP TO HATCH {snap['hatch_at'] - snap['care']}", 13, now % 8, WHITE)

    def current_mascot(self, snap):
        """A fixed mascot, or ("auto") the mascot of whichever school leads the last 5 minutes."""
        if self.mascot != "auto":
            return mascots.MASCOTS[self.mascot]
        board = snap["leaderboard"]
        return mascots.for_school(board[0][0]) if board else mascots.DEFAULT

    def _pet(self, f, snap, events, now, t, party):
        mascot = self.current_mascot(snap)
        sheet = mascot.poses(snap["stage"])
        mood = snap["mood"]
        eating = any(e[1] == "feed" and 0.8 < now - e[0] < 1.6 for e in events)
        if eating:
            pose = "eat"
        elif mood == "sleepy" or time.localtime(now).tm_hour in NIGHT_HOURS:
            pose = "sleep"
        elif mood in ("sad", "hungry", "dirty"):
            pose = "sad"
        elif (t % 4) < 0.15:
            pose = "blink"
        else:
            pose = "idle"
        sprite = sheet[pose]
        h, w = len(sprite), len(sprite[0])
        bottom = GROUND_ROW - 1
        bounce = 0
        if party or mood == "ecstatic":
            bounce = int(abs(math.sin(t * (6 if party else 3))) * (3 if party else 1))
        elif pose == "idle":
            bounce = 1 if (t % 2) < 1 else 0
        top = bottom - h + 1 - bounce
        left = (COLS - w) // 2
        palette = mascot.colors()
        if mood == "dirty":
            palette = {k: mix(v, (90, 60, 20), 0.5) for k, v in palette.items()}
        f.blit(sprite, top, left, palette)
        self.mouth_row = top + next(i for i, row in enumerate(sheet["idle"]) if "M" in row)
        if pose == "sleep":
            for i in range(2):
                phase = (t * 0.6 + i * 0.5) % 1
                f.set(top - 1 - int(phase * 5), left + w - 1 + (i % 2), scale((180, 180, 255), 1 - phase))

    def _ground(self, f, snap, t):
        f.fill_row(GROUND_ROW, (0, 70, 10))
        poops = int((100 - snap["stats"]["clean"]) / 25)
        for i in range(poops):
            f.set(GROUND_ROW, [0, 8, 1, 7][i], (110, 60, 10))

    def _bars(self, f, snap, t):
        for i, stat in enumerate(STAT_NAMES):
            value = snap["stats"][stat]
            lit = math.ceil(value / 100 * COLS)
            color = STAT_COLORS[stat]
            low = value < 20
            for c in range(COLS):
                if c < lit:
                    f.set(BAR_TOP + i, c, (200, 0, 0) if low else color)
                else:
                    f.set(BAR_TOP + i, c, scale(color, 0.06))

    def _particles(self, f, events, now, stage):
        mouth_row = self.mouth_row
        for ts, action, school in events:
            age = now - ts
            col = 1 + _seed(ts) % 7
            if action == "feed" and age < 0.8:
                # Food drops from the top floor into the pet's mouth.
                row = int(1 + (mouth_row - 1) * (age / 0.8) ** 2)
                f.set(row, 4 if age > 0.5 else col, (255, 200, 0))
                f.add(row - 1, 4 if age > 0.5 else col, (255, 120, 0), 0.5)
            elif action == "pet" and age < 1.5:
                row = int(mouth_row - 2 - age * 6)
                f.blit(sprites.HEART, row, col - 1, {"B": scale((255, 40, 120), 1 - age / 1.5)})
            elif action == "play" and age < 1.5:
                x = age / 1.5 * (COLS - 1)
                y = 3 - abs(math.sin(age * 6)) * 2.5
                f.set(int(y), int(x) if _seed(ts) % 2 else COLS - 1 - int(x), schools.color(school))
            elif action == "clean" and age < 0.8:
                for k in range(4):
                    s = _seed(ts + k)
                    f.add(3 + s % 9, s % COLS, (0, 255, 255), 1 - age / 0.8)
            elif action == "cheer" and age < 1.2:
                # Firework: a spark shoots up the edge of the tower and bursts.
                if age < 0.5:
                    f.set(GROUND_ROW - int(age / 0.5 * 10), col, schools.color(school))
                else:
                    r = (age - 0.5) * 4
                    for a in range(8):
                        ang = a * math.pi / 4
                        f.add(round(2 + math.sin(ang) * r), round(col + math.cos(ang) * r),
                              schools.color(school), 1 - (age - 0.5) / 0.7)

    def _leaderboard(self, f, snap, phase):
        board = snap["leaderboard"][:COLS]
        best = board[0][1]
        if phase < 5:
            grow = min(1.0, phase / 1.5)
            for i, (school, count) in enumerate(board):
                height = max(1, round(count / best * (ROWS - 1) * grow))
                for r in range(height):
                    f.set(ROWS - 1 - r, i, schools.color(school))
            return
        leader = board[0][0]
        f.fill_row(0, schools.color(leader))
        f.fill_row(ROWS - 1, schools.color(leader))
        draw_scroll(f, schools.name(leader), 4, phase - 5, schools.color(leader), speed=10)
        draw_number(f, min(best, 99), 10, WHITE)

    def _hatch_show(self, f, age):
        draw_scroll(f, "HATCHED!", 6, age, WHITE, speed=9)

    def _dim(self, f, k):
        for r in range(ROWS):
            for c in range(COLS):
                f.px[r][c] = scale(f.px[r][c], k)
