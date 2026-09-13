"""
Colour ramps.

Two problems with the colours before this file existed.

FIRST: every world was a straight line between two colours. A straight line has
no middle -- you get the dark end, the bright end, and a muddy blend in between.
Real light does not look like that. An aurora is green in its body and magenta
along its lower fringe. A sunset runs indigo to rose to gold. Those need several
stops, not two.

SECOND, and less obvious: mixing colours by averaging their red, green and blue
numbers is wrong. Those numbers are deliberately squashed so that dark tones get
more precision, which means halfway between two numbers is NOT halfway between
two brightnesses. Blend blue and yellow that way and you get mud, because you
are averaging the labels rather than the light.

So this file un-squashes the numbers, mixes, and squashes them back. It is a few
extra lines and it is the difference between colours that look painted and
colours that look lit.
"""

import numpy as np

LUT_SIZE = 64


def _to_linear(c):
    """Undo the squashing, so the numbers stand for actual amounts of light."""
    c = np.asarray(c, dtype=np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _to_srgb(c):
    """Squash it back, so a screen shows what we meant."""
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1 / 2.4)) - 0.055)


def build(stops):
    """
    Turn a list of (position, (r, g, b)) into a smooth 64-step ramp.

    Position runs 0 to 1: 0 is the still, resting surface, 1 is the brightest
    part of a crest. Everything in between is mixed in real light.

    The ramp comes back as ordinary 0-1 colour, ready to display.
    """
    xs = np.array([p for p, _ in stops], dtype=np.float32)
    cols = np.stack([_to_linear(c) for _, c in stops])       # in real light
    grid = np.linspace(0.0, 1.0, LUT_SIZE, dtype=np.float32)
    lin = np.stack([np.interp(grid, xs, cols[:, i]) for i in range(3)], axis=1)
    return _to_srgb(lin).astype(np.float32)


def sample(lut, t):
    """
    Look up a whole picture's worth of colours at once.

    t is any array of 0-to-1 values -- one per window -- and what comes back is
    the same shape with three colour channels on the end.
    """
    idx = np.clip(t, 0.0, 1.0) * (LUT_SIZE - 1)
    lo = np.floor(idx).astype(np.int32)
    hi = np.minimum(lo + 1, LUT_SIZE - 1)
    f = (idx - lo)[..., None]
    return lut[lo] * (1.0 - f) + lut[hi] * f


# ---------------------------------------------------------------------------
# The ramps themselves. This is where the look of the piece actually lives.
# ---------------------------------------------------------------------------

SOUNDING = build([
    (0.00, (8, 12, 40)),      # night air at the top of the column
    (0.30, (18, 62, 132)),
    (0.62, (72, 172, 226)),
    (0.85, (168, 226, 250)),
    (1.00, (236, 246, 255)),  # thin bright cloud
])

AURORA = build([
    (0.00, (4, 16, 26)),
    (0.26, (8, 78, 56)),
    (0.55, (48, 214, 118)),   # the green body, from oxygen high up
    (0.80, (150, 250, 178)),
    (1.00, (214, 104, 235)),  # the magenta lower fringe, from nitrogen.
                              # Real auroras do this, and it is the single
                              # detail that makes one look like an aurora
                              # rather than a green smear.
])

# The standard weather-radar reflectivity scale: green for light returns through
# yellow and orange to red for heavy ones. This is not a decorative choice --
# it is the exact colour scale produced by the radar dome on this building's
# roof, and anyone from the department will recognise it on sight.
RADAR = build([
    (0.00, (2, 14, 22)),
    (0.22, (14, 108, 74)),
    (0.45, (54, 186, 96)),
    (0.64, (206, 220, 62)),
    (0.82, (238, 146, 42)),
    (1.00, (228, 58, 66)),
])

SEISMIC = build([
    (0.00, (14, 6, 12)),      # quiet ground
    (0.30, (96, 18, 32)),
    (0.60, (214, 74, 28)),
    (0.82, (246, 158, 44)),
    (1.00, (255, 232, 170)),  # the arrival
])

REEF = build([
    (0.00, (16, 4, 26)),
    (0.30, (104, 12, 92)),
    (0.62, (226, 52, 138)),
    (0.86, (252, 118, 158)),
    (1.00, (255, 196, 206)),
])

RAMPS = {
    "sounding": SOUNDING,
    "aurora": AURORA,
    "radar": RADAR,
    "seismic": SEISMIC,
    "reef": REEF,
}


# --- the four behaviours that involve people --------------------------------

# Being looked at. Warm, and the warmth is the point: every weather mode in
# this piece is cool, so the moment the building notices you it also gets
# warmer, and that shift is legible from much further away than any shape.
ATTENTION = build([
    (0.00, (10, 8, 26)),
    (0.28, (86, 40, 30)),
    (0.58, (214, 124, 40)),
    (0.82, (252, 200, 116)),
    (1.00, (255, 246, 226)),
])

# A flinch. Cold and electric -- the opposite end of the spectrum from
# attention, so a startle reads instantly as a different kind of event.
STARTLE = build([
    (0.00, (4, 6, 18)),
    (0.30, (18, 58, 132)),
    (0.60, (86, 170, 250)),
    (0.85, (196, 232, 255)),
    (1.00, (255, 255, 255)),
])

# The record of everyone who touched it. Embers on a night sky: each person a
# warm point, the crowd a constellation. Deliberately the most beautiful ramp
# in the file, because this is the one people will be looking at when they
# decide whether to take a photograph.
MEMORY = build([
    (0.00, (8, 6, 30)),
    (0.24, (54, 22, 92)),
    (0.48, (152, 48, 118)),
    (0.70, (238, 118, 82)),
    (0.88, (252, 196, 120)),
    (1.00, (255, 244, 214)),
])

# Replaying the evening. Dusk colours, softer and less saturated than anything
# else here -- a memory of the night rather than the night.
DREAM = build([
    (0.00, (12, 10, 34)),
    (0.30, (62, 46, 112)),
    (0.58, (146, 96, 158)),
    (0.80, (226, 156, 150)),
    (1.00, (250, 222, 198)),
])

RAMPS.update({"attention": ATTENTION, "startle": STARTLE,
              "memory": MEMORY, "dream": DREAM})


# The tree the crowd grows. Bioluminescent rather than autumnal -- deep water
# blue through living green to a pale gold at the growing tips, so the newest
# wood (which is the brightest, see tree.py) reads as the part that is alive
# right now. Distinct from every other ramp here: nothing else goes green
# through gold.
TREE = build([
    (0.00, (6, 14, 34)),
    (0.26, (12, 74, 86)),
    (0.52, (38, 168, 118)),
    (0.74, (142, 226, 122)),
    (0.90, (232, 240, 150)),
    (1.00, (255, 250, 214)),
])
# The forecast. Not chosen to be pretty -- chosen so a stranger can read it
# without being told: dark is clear sky, grey is cloud, bright cyan-white is
# rain. Nothing in the middle competes for attention, so the only thing that
# catches your eye from across the river is the weather that is coming.
FORECAST = build([
    (0.00, (5, 10, 26)),        # clear night
    (0.30, (44, 56, 84)),       # cloud
    (0.55, (96, 126, 158)),     # thick cloud
    (0.76, (86, 196, 226)),     # rain likely
    (1.00, (222, 250, 255)),    # rain certain
])

RAMPS["tree"] = TREE
RAMPS["forecast"] = FORECAST
