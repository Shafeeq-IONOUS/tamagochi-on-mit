"""
The surge.

A building that does the same thing continuously is wallpaper. People glance
at it and walk on. What makes somebody stop, and then stay, and then get their
phone out, is a RARE event -- something that does not happen most of the time,
so that seeing it feels like having caught something.

So every couple of minutes, whatever else it is doing, the building takes one
enormous breath:

    SETTLE   (3.5s)  everything sinks and dims. The facade goes quiet.
                     This is the part that makes people look up -- a big thing
                     getting suddenly darker is far more arresting than a big
                     thing getting brighter.
    HOLD     (1.2s)  almost nothing. An uncomfortably long pause.
    RISE     (2.6s)  a single bright front climbs all twenty-one storeys.
    BLOOM    (1.4s)  it reaches the roof and opens.
    RECOVER  (4.0s)  sinks back into whatever it was doing before.

About thirteen seconds, once every ninety to two hundred. The waiting is not a
side effect, it is the mechanism: a crowd that has seen it once will stand and
wait to see it again, and that is the difference between a passer-by and an
audience.

It also respects the safety rules by construction. The dimming and the swell
are slower than the strobe limit, and the bright part is a narrow band rather
than the whole facade -- so the governor never has to fight it.
"""

import random
import numpy as np

ROWS, COLS, SCALE = 17, 9, 4
HI_ROWS, HI_COLS = ROWS * SCALE, COLS * SCALE

_Y = np.repeat((np.arange(HI_ROWS, dtype=np.float32) + 0.5).reshape(-1, 1) / HI_ROWS,
               HI_COLS, axis=1)
_X = np.repeat((np.arange(HI_COLS, dtype=np.float32) + 0.5).reshape(1, -1) / HI_COLS,
               HI_ROWS, axis=0)

SETTLE, HOLD, RISE, BLOOM, RECOVER = 3.5, 1.2, 2.6, 1.4, 4.0
TOTAL = SETTLE + HOLD + RISE + BLOOM + RECOVER


def _down(hi):
    return hi.reshape(ROWS, SCALE, COLS, SCALE).mean(axis=(1, 3))


class Surge:
    """Runs the rare event and reports what it wants done to the picture."""

    def __init__(self, gap=(90.0, 200.0)):
        self._gap = gap
        self._next = random.uniform(*gap) * 0.45   # first one comes sooner
        self._began = None

    def trigger(self, t):
        """Force one now. Bound to a key, so you can call it in a demo."""
        self._began = t

    @property
    def active(self):
        return self._began is not None

    def update(self, t, calm):
        """
        Decide whether to start one, and say where it is up to.

        Only starts when the building is calm. Interrupting somebody's own
        interaction with a scripted set piece would undo the thing that makes
        the piece work.

        Returns (dim, glow) -- a number to multiply the whole picture by, and
        a 17x9 field to add on top.
        """
        if self._began is None:
            if calm and t >= self._next:
                self._began = t
            else:
                if not calm:
                    self._next = max(self._next, t + 25.0)   # try again later
                return 1.0, None

        age = t - self._began
        if age >= TOTAL:
            self._began = None
            self._next = t + random.uniform(*self._gap)
            return 1.0, None

        return self._shape(age)

    def _shape(self, age):
        ease = lambda x: x * x * (3.0 - 2.0 * x)

        if age < SETTLE:
            p = ease(age / SETTLE)
            return 1.0 - 0.80 * p, None

        if age < SETTLE + HOLD:
            return 0.20, None

        a = age - SETTLE - HOLD

        if a < RISE:
            p = ease(a / RISE)
            front = 1.0 - p * 1.05                 # ground to roof
            d = _Y - front
            band = np.exp(-(d * d) / (2 * 0.045 ** 2))
            # A little wider at the edges, so it reads as a wave and not a bar.
            band *= 0.75 + 0.35 * np.abs(_X - 0.5) * 2.0
            tail = 0.35 * np.exp(-np.clip(d, 0, 9) / 0.16)
            return 0.20 + 0.35 * p, _down((band * 2.6 + tail).astype(np.float32))

        a -= RISE
        if a < BLOOM:
            p = a / BLOOM
            # Opens out from the roof, then softens.
            spread = 0.05 + 0.55 * ease(p)
            crown = np.exp(-(_Y * _Y) / (2 * spread * spread))
            return 0.55 + 0.25 * p, _down((crown * 2.9 * (1.0 - 0.55 * p)).astype(np.float32))

        a -= BLOOM
        p = ease(a / RECOVER)
        glow = np.exp(-(_Y * _Y) / (2 * 0.6 ** 2)) * 0.9 * (1.0 - p)
        return 0.80 + 0.20 * p, _down(glow.astype(np.float32))

    def phase(self):
        """What it is doing right now, for the status bar."""
        if self._began is None:
            return ""
        return "SURGE"
