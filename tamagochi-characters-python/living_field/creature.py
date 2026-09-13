"""
The creature.

Everything else in this project is a way of DRAWING. This file is the part that
has a state of mind -- and it is what makes the difference between a light show
and something embodied.

A body is not just a surface that reacts. It has internal conditions that
persist, build up, and decay on their own: how alert it is, how curious, how
tired, and what it remembers. The same touch lands differently on a creature
that has been alone for an hour than on one that has been crowded all evening.

None of that is visible directly. What you see is how it chooses to express
itself, which is decided in brain.py from the numbers kept here.

Nothing in this file draws anything, and nothing here runs at frame rate. It is
updated twice a second, well away from the thirty-frames-a-second half.
"""

import time
from collections import deque


class Creature:
    """The building's internal condition."""

    # Nothing lasts forever. Each of these is how long it takes a feeling to
    # fall to roughly a third of its strength, with nothing new happening.
    AROUSAL_HALFLIFE = 14.0     # excitement fades fastest
    CURIOSITY_HALFLIFE = 40.0   # interest lingers
    FATIGUE_HALFLIFE = 210.0    # tiredness takes minutes to shake off

    # How many touches it keeps. Not a technical limit -- this is how much of an
    # evening the building can hold in mind at once.
    MEMORY_SIZE = 400

    def __init__(self):
        self.arousal = 0.0      # how activated it is right now
        self.curiosity = 0.15   # how much it wants something to happen
        self.fatigue = 0.0      # builds with activity, only rest clears it
        self.touches = deque(maxlen=self.MEMORY_SIZE)   # (t, row, col, weight)
        self.last_touch_at = -1e9
        self.first_touch_at = None
        self.born = time.time()
        self._last_tick = 0.0

    # -- things that happen to it -----------------------------------------
    def touched(self, t, row, col, weight=1.0):
        """
        Somebody made contact.

        Arousal jumps. Curiosity rises, but less if this keeps happening --
        the tenth person in a minute is less interesting than the first, which
        is true of animals and true of people.
        """
        self.touches.append((t, row, col, weight))
        self.last_touch_at = t
        if self.first_touch_at is None:
            self.first_touch_at = t

        recent = self.touch_rate(t, window=30.0)
        novelty = 1.0 / (1.0 + 1.4 * recent)

        self.arousal = min(1.0, self.arousal + 0.55 * weight)
        self.curiosity = min(1.0, self.curiosity + 0.40 * weight * novelty)
        self.fatigue = min(1.0, self.fatigue + 0.045 * weight)

    def attended(self, t, closeness):
        """Somebody is near, but has not touched. A held presence, not an event."""
        if closeness <= 0.05:
            return
        self.arousal = min(1.0, self.arousal + 0.012 * closeness)
        self.curiosity = min(1.0, self.curiosity + 0.020 * closeness)
        self.last_touch_at = max(self.last_touch_at, t - 2.0)

    # -- the passage of time ----------------------------------------------
    def tick(self, t):
        """Let feelings decay. Called twice a second, not every frame."""
        dt = max(0.0, t - self._last_tick)
        self._last_tick = t
        if dt <= 0:
            return

        def decay(v, halflife):
            return v * (0.5 ** (dt / halflife))

        self.arousal = decay(self.arousal, self.AROUSAL_HALFLIFE)
        self.curiosity = decay(self.curiosity, self.CURIOSITY_HALFLIFE)
        self.fatigue = decay(self.fatigue, self.FATIGUE_HALFLIFE)

        # Left alone for long enough, it gets restless rather than flat.
        # A creature with nothing to do does not sit at zero.
        if t - self.last_touch_at > 90.0:
            self.curiosity = min(0.75, self.curiosity + 0.004 * dt)

    # -- what it knows about itself ---------------------------------------
    def touch_rate(self, t, window=60.0):
        """Touches per minute, over the last little while."""
        n = sum(1 for (tt, _, _, _) in self.touches if t - tt <= window)
        return n * (60.0 / window)

    def focus(self, t, window=25.0):
        """
        Where its attention is: the average place it was last touched.

        Returns (row, col) as 0-to-1, or None if nothing recent. This is what
        makes it lean towards somebody rather than just brighten.
        """
        pts = [(r, c, w) for (tt, r, c, w) in self.touches if t - tt <= window]
        if not pts:
            return None
        tw = sum(w for _, _, w in pts) or 1.0
        return (sum(r * w for r, _, w in pts) / tw,
                sum(c * w for _, c, w in pts) / tw)

    def since_touch(self, t):
        return t - self.last_touch_at

    def facts(self, t):
        """
        Describe itself in words a rule engine can reason about.

        Deliberately coarse. The brain should reason about "alert and curious
        and recently touched", not about 0.6187 -- and coarse symbols are also
        what makes the rules readable by a person.
        """
        def band(v, lo=0.33, hi=0.66):
            return "low" if v < lo else ("mid" if v < hi else "high")

        since = self.since_touch(t)
        if since < 2.5:
            contact = "just-now"
        elif since < 25.0:
            contact = "recent"
        elif since < 120.0:
            contact = "a-while"
        else:
            contact = "alone"

        rate = self.touch_rate(t)
        crowd = "none" if rate < 0.5 else ("some" if rate < 6 else "many")

        return {
            "contact": contact,
            "arousal": band(self.arousal),
            "curiosity": band(self.curiosity),
            "fatigue": band(self.fatigue),
            "crowd": crowd,
            "remembered": len(self.touches),
        }
