"""
KING OF THE CHARLES.

Four crews race up the building. Whoever is highest is winning, and that is the
whole of the rules -- which matters, because height is the one thing that
survives four hundred metres of night air. Everything else in this project had
to be argued into legibility. A race is legible by construction.

It is also the building's own river. The Head of the Charles is the largest
rowing regatta in the world, it happens on that water every October, and all
four of these schools race it. This is not a theme applied to the site; it is
the site.

THE LANES

Nine columns, four crews:

    0 1 | 2 3 | (4) | 5 6 | 7 8
    HARV  MIT   ---   NEU   BU

Two columns each and a dark channel down the middle, which stops the two
middle lanes bleeding into each other once the distance blurs everything.

ABOUT THE COLOURS, HONESTLY

Harvard crimson, MIT cardinal, BU scarlet and Northeastern red are, at this
resolution and through haze, the same colour. Four reds is not a race anybody
can watch. So each crew keeps whatever is distinctive about its own palette and
the collisions were moved apart on purpose:

    Harvard      crimson          theirs, unchanged
    MIT          silver-white     MIT's silver, and the only pale lane
    Northeastern deep red-black   pushed cool and dark, theirs is red AND black
    BU           scarlet-gold     pushed warm, so it cannot be mistaken for crimson

Say that out loud rather than hoping nobody notices. It is a legibility
decision, and it is the kind of decision this whole project is about.
"""

import numpy as np

ROWS, COLS, SCALE = 17, 9, 4
HI_ROWS, HI_COLS = ROWS * SCALE, COLS * SCALE

_Y = np.repeat((np.arange(HI_ROWS, dtype=np.float32) + 0.5).reshape(-1, 1) / HI_ROWS,
               HI_COLS, axis=1)
_X = np.repeat((np.arange(HI_COLS, dtype=np.float32) + 0.5).reshape(1, -1) / HI_COLS,
               HI_ROWS, axis=0)


def _down(hi):
    return hi.reshape(ROWS, SCALE, COLS, SCALE).mean(axis=(1, 3))


class Crew:
    __slots__ = ("name", "short", "colour", "lane", "pos", "speed", "strokes", "puff")

    def __init__(self, name, short, colour, lane):
        self.name = name
        self.short = short
        self.colour = np.array(colour, dtype=np.float32) / 255.0
        self.lane = lane          # centre of the lane, 0 to 1 across
        self.pos = 0.0            # 0 at the start line, 1 at the finish
        self.speed = 0.0
        self.strokes = 0          # taps from the crowd since the last update
        self.puff = 0.0           # brief flare when somebody rows


CREWS = [
    Crew("Harvard",      "HARV", (165, 28, 48),  1.5 / 9),   # crimson, theirs
    Crew("MIT",          "MIT",  (226, 232, 238), 3.5 / 9),  # silver, theirs
    Crew("Northeastern", "NEU",  (120, 20, 60),  6.5 / 9),   # pushed cool
    Crew("BU",           "BU",   (255, 150, 40),  8.5 / 9),  # pushed warm
]

# How fast a crew can possibly go, and how quickly it slows without rowing.
#
# Tuned so a hard-rowed race lasts about a minute. The first version finished in
# eight seconds, which is not a crowd moment -- people need long enough to
# realise they are in a race, pick a side, and start shouting.
MAX_SPEED = 0.021          # of the course per second, flat out
DRAG = 0.85                # a boat that stops being rowed stops moving
STROKE = 0.0055            # what one tap is worth
DRIFT = 0.0048             # a little pace with nobody rowing, so an unloved
                           # crew still moves and the race always ends


class Race:
    """The race itself. Knows nothing about colour ramps or the governor."""

    def __init__(self, seed=None):
        import random
        self._rng = random.Random(seed)
        self.reset()

    def reset(self):
        for i, c in enumerate(CREWS):
            c.pos = 0.0
            c.speed = 0.0
            c.strokes = 0
            c.puff = 0.0
        self.winner = None
        self.finished_at = None
        self.running = False
        self.t0 = 0.0

    def start(self, t):
        self.reset()
        self.running = True
        self.t0 = t

    def row(self, crew_index, n=1):
        """Somebody pulled. Only counts while the race is running."""
        if self.running and 0 <= crew_index < len(CREWS):
            CREWS[crew_index].strokes += n
            CREWS[crew_index].puff = 1.0

    # How much a trailing crew claws back. Without this the school with the
    # most people in the room saturates and runs away in the first ten seconds,
    # which is fair and completely undramatic -- and a runaway has no finish
    # worth setting off fireworks for.
    #
    # With it, being behind is worth something and the lead changes hands. It
    # is the same rubber band every racing game has used for thirty years, for
    # exactly this reason.
    CATCHUP = 0.55

    def step(self, dt, t):
        if not self.running:
            return
        front = max(c.pos for c in CREWS)
        for c in CREWS:
            c.speed += c.strokes * STROKE
            c.strokes = 0
            c.speed = min(c.speed, MAX_SPEED)
            c.speed *= (1.0 - DRAG * dt)
            behind = max(0.0, front - c.pos)
            boost = 1.0 + self.CATCHUP * min(behind / 0.25, 1.0)
            c.pos = c.pos + (c.speed * boost + DRIFT) * dt
            c.puff = max(0.0, c.puff - dt * 2.2)

        # Who crossed, and by how much.
        #
        # Because the catch-up makes nearly every race a photo finish, crews
        # regularly cross on the same frame. Taking the first one in the list
        # handed Harvard 44% of dead-even races purely for being written first.
        # The winner is whoever is furthest past the line, and an exact tie is
        # settled by a coin toss rather than by list order.
        crossed = [c for c in CREWS if c.pos >= 1.0]
        if crossed and self.winner is None:
            best = max(c.pos for c in crossed)
            tied = [c for c in crossed if c.pos >= best - 1e-9]
            self.winner = tied[0] if len(tied) == 1 else self._rng.choice(tied)
            self.finished_at = t
            self.running = False

        for c in CREWS:
            c.pos = min(1.0, c.pos)

    @property
    def leader(self):
        return max(CREWS, key=lambda c: c.pos)

    def standings(self):
        return sorted(CREWS, key=lambda c: -c.pos)

    # -- drawing -----------------------------------------------------------
    def render(self, t):
        """The course, as a 17 x 9 x 3 picture of 0 to 1."""
        out = np.zeros((HI_ROWS, HI_COLS, 3), dtype=np.float32)

        # The water: a dark moving surface, so the course is never dead.
        water = 0.035 + 0.022 * np.sin(2 * np.pi * (0.13 * t + _Y * 2.2 + _X * 0.7))
        out += water[:, :, None] * np.array([0.25, 0.45, 0.75], dtype=np.float32)

        for c in CREWS:
            dx = np.abs(_X - c.lane)
            lane = np.exp(-(dx * dx) / (2 * 0.052 ** 2))

            # Where the boat is. Row 0 is the roof, so the finish is the top.
            y = 1.0 - c.pos * 0.94 - 0.03
            dy = _Y - y

            # The boat: a short bright bar.
            boat = np.exp(-(dy * dy) / (2 * 0.022 ** 2))

            # The wake behind it, longer the faster it is going.
            length = 0.05 + 2.6 * c.speed
            wake = np.exp(-np.clip(dy, 0, 9) / length) * 0.55

            # A flare on the stroke, so a tap is visible instantly. This is the
            # feedback that makes a crowd keep pressing.
            flare = c.puff * np.exp(-(dy * dy) / (2 * 0.05 ** 2)) * 0.9

            strength = (boat * 1.5 + wake + flare) * lane
            out += strength[:, :, None] * c.colour

        # The finish line, so the top of the course is a place and not an edge.
        fin = np.exp(-((_Y - 0.03) ** 2) / (2 * 0.012 ** 2)) * 0.16
        out += fin[:, :, None]

        return np.clip(np.stack([_down(out[:, :, i]) for i in range(3)], axis=2),
                       0.0, 1.0)


# ===========================================================================
#  THE FINALE
#
#  What you cannot have: crackling fireworks. The safety limit says no window
#  may go from dark to full in under about a second and a half, and a crackle
#  is a tenth of that. Trying anyway would just be smoothed into mush by the
#  governor, and would deserve to be.
#
#  What you can have, and what is actually right: the fireworks you see from
#  across a river. At that distance the crackle is gone already -- what reaches
#  you is the swelling, the climb, the slow fall and the afterglow. That is the
#  part that makes people stop walking, and every bit of it is slow enough to
#  be legal.
#
#  Eleven seconds, in four movements:
#
#    LAUNCH   0.0-1.6   the winner's colour climbs out of their own lane
#    BURST    1.6-4.5   it opens across the whole building
#    FALL     4.5-8.0   embers drift down and the roof holds a glow
#    NAME     8.0-11.0  it settles, and the tower says who won
# ===========================================================================

LAUNCH, BURST, FALL, NAME = 1.6, 2.9, 3.5, 3.0
FINALE = LAUNCH + BURST + FALL + NAME


def finale(age, crew, t):
    """
    The celebration, as a 17 x 9 x 3 picture of 0 to 1.

    `age` is seconds since the crew crossed the line.
    """
    out = np.zeros((HI_ROWS, HI_COLS, 3), dtype=np.float32)
    col = crew.colour
    warm = np.clip(col * 0.55 + np.array([0.45, 0.35, 0.18], dtype=np.float32), 0, 1)

    if age < LAUNCH:
        # A rocket leaving their lane. Fast in SPACE, which is allowed --
        # it is windows that may not blink, not shapes that may not move.
        p = age / LAUNCH
        y = 1.0 - p * 0.86
        dx = np.abs(_X - crew.lane)
        dy = _Y - y
        head = np.exp(-(dy * dy) / (2 * 0.030 ** 2)) * np.exp(-(dx * dx) / (2 * 0.055 ** 2))
        trail = np.exp(-np.clip(dy, 0, 9) / 0.30) * np.exp(-(dx * dx) / (2 * 0.045 ** 2)) * 0.5
        out += ((head * 1.7 + trail) * (0.4 + 0.6 * p))[:, :, None] * col
        return _finish(out)

    a = age - LAUNCH
    if a < BURST:
        # Opening. Three shells, staggered, each swelling rather than popping.
        p = a / BURST
        for k, (cx, cy, delay, size) in enumerate(
                ((0.5, 0.16, 0.0, 1.00), (0.26, 0.30, 0.55, 0.72), (0.76, 0.26, 0.95, 0.78))):
            local = a - delay
            if local <= 0:
                continue
            q = min(1.0, local / (BURST - delay))
            r = 0.06 + size * 0.75 * (q ** 0.55)
            d = np.sqrt((_X - cx) ** 2 + (_Y - cy) ** 2)
            shell = np.exp(-((d - r) ** 2) / (2 * (0.055 + 0.10 * q) ** 2))
            core = np.exp(-(d * d) / (2 * (0.10 + 0.16 * q) ** 2)) * (1.0 - q)
            fade = (1.0 - q) ** 0.7
            c = col if k == 0 else warm
            out += ((shell * 1.25 + core * 1.1) * fade)[:, :, None] * c
        # The whole building carries the colour while it is open.
        out += (0.16 * (1.0 - p)) * col.reshape(1, 1, 3)
        return _finish(out)

    a -= BURST
    if a < FALL:
        # Embers coming down, and a glow left on the roof.
        p = a / FALL
        fall = 0.0
        for i in range(9):
            sx = (i * 0.113 + 0.07) % 1.0
            sy = 0.16 + 0.80 * (p ** 1.35) + 0.10 * np.sin(i * 2.1)
            dx = _X - sx
            dy = _Y - sy
            fall = np.maximum(fall, np.exp(-(dx * dx) / (2 * 0.035 ** 2)
                                           - (dy * dy) / (2 * 0.045 ** 2)))
        drift = fall * (1.0 - p) * 1.15
        roof = np.exp(-(_Y ** 2) / (2 * 0.30 ** 2)) * 0.42 * (1.0 - p * 0.7)
        out += drift[:, :, None] * warm + roof[:, :, None] * col
        return _finish(out)

    # Settling. The name is drawn over the top of this by run.py.
    a -= FALL
    p = min(1.0, a / NAME)
    glow = (0.30 * (1.0 - p * 0.55)) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.5 * t))
    out += glow * col.reshape(1, 1, 3)
    return _finish(out)


def _finish(hi):
    return np.clip(np.stack([_down(hi[:, :, i]) for i in range(3)], axis=2), 0.0, 1.0)
