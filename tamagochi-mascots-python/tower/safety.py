"""Photosensitivity guard for a building-sized display.

WCAG 2.3.1: content must not flash more than 3 times in any 1 second. A flash is a pair of
opposing changes in relative luminance of 10% or more, where the darker state is below 0.8.
A whole facade is a very large visual field, so we enforce a stricter budget and enforce it
in code, on every window and on the facade as a whole:

1. Slew: a window's R, G, B may move at most MAX_STEP per frame, so hard cuts become soft fades.
2. Reversal budget: each window (and the facade average) is tracked with the WCAG flash
   definition; a frame change that would push it past GUARD_FLASHES_PER_SECOND is held back
   until the budget frees up.

Apps should still avoid flashy effects instead of leaning on the guard; tests/test_safety.py
runs every shipped animation through worst_flash_rate().
"""

from collections import deque

from tower.display import COLS, MAX_FPS, ROWS, Frame

MAX_FLASHES_PER_SECOND = 3     # WCAG 2.3.1 general flash threshold
GUARD_FLASHES_PER_SECOND = 2   # what the guard allows - margin under the threshold
RAMP_SECONDS = 0.3             # a 0 -> 255 fade takes at least this long
MAX_STEP = max(1, round(255 / (RAMP_SECONDS * MAX_FPS)))
FLASH_DELTA = 0.1
DARK_BELOW = 0.8


def _linear(v):
    v /= 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


_LIN = [_linear(v) for v in range(256)]


def luminance(rgb):
    """WCAG relative luminance, 0..1."""
    return 0.2126 * _LIN[rgb[0]] + 0.7152 * _LIN[rgb[1]] + 0.0722 * _LIN[rgb[2]]


class FlashTracker:
    """Counts WCAG transitions (half-flashes) on one luminance signal."""

    def __init__(self, v=0.0, fps=MAX_FPS):
        self.fps = fps
        self.lo = self.hi = v
        self.direction = 0
        self.marks = deque()

    def _flip(self, v):
        """New direction if luminance v would count as a transition, else None."""
        hi, lo = max(self.hi, v), min(self.lo, v)
        if self.direction >= 0 and hi - v >= FLASH_DELTA and v < DARK_BELOW:
            return -1
        if self.direction <= 0 and v - lo >= FLASH_DELTA and lo < DARK_BELOW:
            return 1
        return None

    def recent(self, i):
        while self.marks and self.marks[0] <= i - self.fps:
            self.marks.popleft()
        return len(self.marks)

    def allows(self, v, i, per_second):
        return self._flip(v) is None or self.recent(i) < 2 * per_second

    def commit(self, v, i):
        flip = self._flip(v)
        self.hi, self.lo = max(self.hi, v), min(self.lo, v)
        if flip is not None:
            self.marks.append(i)
            self.direction = flip
            self.hi = self.lo = v
        return self.recent(i)


class FlashGuard:
    def __init__(self, display=None, max_step=MAX_STEP, per_second=GUARD_FLASHES_PER_SECOND):
        self.display = display
        self.max_step = max_step
        self.per_second = per_second
        self.shown = Frame()
        self.trackers = [[FlashTracker() for _ in range(COLS)] for _ in range(ROWS)]
        self.facade = FlashTracker()
        self.i = 0

    def filter(self, frame):
        step, i = self.max_step, self.i
        out = Frame()
        for r in range(ROWS):
            for c in range(COLS):
                prev, want = self.shown.px[r][c], frame.px[r][c]
                nxt = tuple(p + max(-step, min(step, w - p)) for p, w in zip(prev, want))
                tracker = self.trackers[r][c]
                if not tracker.allows(luminance(nxt), i, self.per_second):
                    nxt = prev
                tracker.commit(luminance(nxt), i)
                out.px[r][c] = nxt
        mean = sum(luminance(p) for row in out.px for p in row) / (ROWS * COLS)
        if not self.facade.allows(mean, i, self.per_second):
            out = self.shown  # the whole facade would flash: hold the last frame
            mean = sum(luminance(p) for row in out.px for p in row) / (ROWS * COLS)
            for r in range(ROWS):
                for c in range(COLS):
                    self.trackers[r][c].commit(luminance(out.px[r][c]), i)
        self.facade.commit(mean, i)
        self.shown = out
        self.i += 1
        return out

    def send(self, frame):
        self.display.send(self.filter(frame))


def worst_flash_rate(frames, fps=MAX_FPS):
    """Highest flashes per second in any 1 s window, as (rate, where); where is (row, col) or "facade"."""
    trackers = {(r, c): None for r in range(ROWS) for c in range(COLS)}
    trackers["facade"] = None
    worst = (0.0, None)
    for i, f in enumerate(frames):
        values = {(r, c): luminance(f.px[r][c]) for r in range(ROWS) for c in range(COLS)}
        values["facade"] = sum(values.values()) / (ROWS * COLS)
        for where, v in values.items():
            if trackers[where] is None:
                trackers[where] = FlashTracker(v, fps)
            rate = trackers[where].commit(v, i) / 2
            if rate > worst[0]:
                worst = (rate, where)
    return worst
