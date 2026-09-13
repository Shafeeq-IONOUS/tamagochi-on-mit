"""
Worlds.

A world is not a picture. It is a set of laws: what the surface is made of, what
shape moves across it, how it breathes when nothing is happening, and what
colour it is.

Changing world does not cut to a new scene. Every law slides into the new one
over about four seconds, so you watch the building reorganise itself. That
reorganising IS the "world transition" effect in the hackathon brief -- it looks
like the building is being carried somewhere, because it is.

WHY THESE FIVE

The Green Building houses MIT's Department of Earth, Atmospheric and Planetary
Sciences, and there is a weather radar dome on its roof. So rather than
decorating it with abstract physics, each world is one of the things the people
inside actually study -- and each happens to suit a tall narrow tower, because
soundings, auroras and seismic traces are all naturally drawn as vertical
columns.

An earlier version had three worlds that differed only in colour and speed.
Measured at true scale they were the same picture three times. Each of these has
a different SHAPE, which is what actually survives the distance.

THIS IS THE FILE TO PLAY WITH. All the design is in these numbers.
"""

import numpy as np
from dataclasses import dataclass, fields as dataclass_fields

from living_field import ramps


@dataclass
class World:
    name: str
    subtitle: str          # one line, for the status bar and the pitch

    # --- what the surface is made of ---
    # 0.0 = the wave field (ripples, field.py)
    # 1.0 = the living skin (reaction-diffusion, reaction.py)
    substrate_mix: float

    # True for the one world that is made of a grown structure rather than a
    # field. Kept as a flag rather than folded into substrate_mix because a
    # tree cannot be half-crossfaded with a wave -- the two are drawn
    # separately and dissolved between.
    is_tree: bool

    # --- the shape that moves across it ---
    texture: str           # a name from patterns.PATTERNS
    texture_amount: float  # how strongly the pattern shows
    field_amount: float    # how strongly a person's touch shows through it

    # How fast the pattern moves. Measured, not guessed: below about 0.4 change
    # per half-second a pattern reads as a still image, and above about 0.95 it
    # reads as agitated. These are each tuned to sit in between.
    time_scale: float

    # --- how the surface behaves ---
    speed: float           # how fast ripples travel (keep under ~0.5)
    damping: float         # how slowly they fade (1.0 = rings forever)
    poke_strength: float
    poke_radius: float

    # --- how it behaves with nobody there ---
    breath_rate: float     # breaths per second
    breath_depth: float    # how deep, as a fraction
    breath_travel: float   # how far the breath is spread down the tower.
                           # 0 makes the whole face swell at once, which reads
                           # as a flat panel from across the river.
    drift_depth: float     # slow uneven shimmer, so it is never perfectly even

    # --- brightness ---
    level: float
    ripple_boost: float

    # --- colour ---
    # A ramp of 64 colours running from the still, resting surface to the
    # brightest part of a crest. Defined in ramps.py, mixed in real light so
    # the middle of the ramp is a colour rather than mud. Two-colour versions
    # of this looked flat, because a straight line between two colours has no
    # middle worth looking at.
    ramp: np.ndarray

    # Which slice of the ramp this world's surface actually reaches, measured
    # from the running system. The top end is deliberately set a little ABOVE
    # what the surface reaches for the busiest worlds -- otherwise a third of
    # the windows sit exactly at the brightness cap and every distinction
    # between bright and brightest is thrown away. Stretching that slice across the whole ramp is
    # what makes the colours at the ends -- an aurora's magenta fringe, the red
    # of a heavy radar return -- actually appear. Without it the best colours
    # in the ramp are defined and then never seen.
    ramp_range: tuple

    gain: float
    response: float        # below 1.0 lifts faint, far-travelled light so it
                           # is still visible after climbing the whole tower


SOUNDING = World(
    name="Sounding", subtitle="the air above one spot, layer by layer",
    substrate_mix=0.0, is_tree=False, texture="sounding", time_scale=8.0, texture_amount=0.80, field_amount=0.55,
    speed=0.30, damping=0.9965, poke_strength=0.9, poke_radius=0.16,
    breath_rate=0.07, breath_depth=0.22, breath_travel=0.70, drift_depth=0.14,
    level=0.60, ripple_boost=1.25,
    ramp=ramps.SOUNDING, ramp_range=(0.16, 0.84),
    gain=0.85, response=0.55,
)

AURORA = World(
    name="Aurora", subtitle="curtains hanging in the upper atmosphere",
    substrate_mix=0.0, is_tree=False, texture="aurora", time_scale=3.5, texture_amount=0.88, field_amount=0.45,
    speed=0.26, damping=0.9970, poke_strength=0.9, poke_radius=0.14,
    breath_rate=0.05, breath_depth=0.26, breath_travel=0.50, drift_depth=0.18,
    level=0.58, ripple_boost=1.3,
    ramp=ramps.AURORA, ramp_range=(0.08, 0.92),
    gain=0.80, response=0.55,
)

SEISMIC = World(
    name="Seismic", subtitle="a wave arriving through rock",
    substrate_mix=0.0, is_tree=False, texture="seismic", time_scale=1.6, texture_amount=0.92, field_amount=0.70,
    speed=0.52, damping=0.995, poke_strength=1.5, poke_radius=0.07,
    breath_rate=0.22, breath_depth=0.14, breath_travel=1.10, drift_depth=0.08,
    level=0.56, ripple_boost=1.7,
    ramp=ramps.SEISMIC, ramp_range=(0.14, 0.97),
    gain=1.20, response=0.45,
)

RADAR = World(
    name="Radar", subtitle="the dome on the roof, sweeping",
    substrate_mix=0.0, is_tree=False, texture="radar", time_scale=1.0, texture_amount=0.90, field_amount=0.40,
    speed=0.34, damping=0.996, poke_strength=0.9, poke_radius=0.12,
    breath_rate=0.09, breath_depth=0.16, breath_travel=0.60, drift_depth=0.10,
    level=0.58, ripple_boost=1.35,
    ramp=ramps.RADAR, ramp_range=(0.21, 1.22),
    gain=0.90, response=0.50,
)

REEF = World(
    name="Reef", subtitle="a living skin that never repeats",
    # Not made of waves at all: Turing's reaction-diffusion, the maths behind
    # leopard spots and seashells. It sustains itself indefinitely, and a touch
    # plants a colony that grows rather than a ripple that fades.
    substrate_mix=1.0, is_tree=False, texture="none", time_scale=1.0, texture_amount=0.0, field_amount=1.00,
    speed=0.0, damping=1.0, poke_strength=1.0, poke_radius=0.09,
    breath_rate=0.05, breath_depth=0.22, breath_travel=0.45, drift_depth=0.10,
    level=0.62, ripple_boost=1.4,
    ramp=ramps.REEF, ramp_range=(0.18, 0.96),
    gain=1.00, response=0.50,
)

# ===========================================================================
#  The four that involve people.
#
#  Everything above is weather: it runs the same whether anybody is there or
#  not. These four exist only because somebody is, and the building chooses
#  them for itself -- see brain.metta.
# ===========================================================================

ATTENTION = World(
    name="Attention", subtitle="it has noticed you",
    substrate_mix=0.0, is_tree=False, texture="attention", time_scale=1.0,
    texture_amount=0.95, field_amount=0.35,
    speed=0.30, damping=0.995, poke_strength=0.8, poke_radius=0.13,
    breath_rate=0.16, breath_depth=0.14, breath_travel=0.35, drift_depth=0.07,
    level=0.62, ripple_boost=1.4,
    ramp=ramps.ATTENTION, ramp_range=(0.24, 0.92),
    gain=0.90, response=0.50,
)

STARTLE = World(
    name="Startle", subtitle="it flinched",
    substrate_mix=0.0, is_tree=False, texture="startle", time_scale=1.0,
    texture_amount=1.00, field_amount=0.55,
    speed=0.52, damping=0.988, poke_strength=1.6, poke_radius=0.06,
    breath_rate=0.40, breath_depth=0.08, breath_travel=1.30, drift_depth=0.05,
    level=0.58, ripple_boost=2.0,
    ramp=ramps.STARTLE, ramp_range=(0.31, 0.72),
    gain=1.30, response=0.45,
)

MEMORY = World(
    name="Memory", subtitle="everyone who touched it tonight",
    substrate_mix=0.0, is_tree=False, texture="memory", time_scale=1.0,
    texture_amount=0.98, field_amount=0.30,
    speed=0.24, damping=0.997, poke_strength=1.0, poke_radius=0.09,
    breath_rate=0.06, breath_depth=0.20, breath_travel=0.55, drift_depth=0.12,
    level=0.60, ripple_boost=0.62,
    ramp=ramps.MEMORY, ramp_range=(0.52, 1.06),
    gain=0.95, response=0.52,
)

DREAM = World(
    name="Dream", subtitle="replaying the evening",
    substrate_mix=0.0, is_tree=False, texture="dream", time_scale=1.0,
    texture_amount=0.95, field_amount=0.25,
    speed=0.22, damping=0.997, poke_strength=0.7, poke_radius=0.14,
    breath_rate=0.04, breath_depth=0.26, breath_travel=0.45, drift_depth=0.16,
    level=0.56, ripple_boost=1.4,
    ramp=ramps.DREAM, ramp_range=(0.25, 0.87),
    gain=0.85, response=0.55,
)


# Keys 1-9, in order.
TREE = World(
    name="Tree", subtitle="the crowd grows one tree, all evening",
    # The only world made of a structure rather than a field. Every person who
    # touches the building grafts a limb onto the tree that is already there --
    # the first of the night plants the trunk, the hundredth adds a twig -- and
    # the branches stay. Branching is also the one kind of shape that survives
    # 153 windows, because a branch looks the same at every scale.
    substrate_mix=0.0, is_tree=True, texture="none", time_scale=1.0,
    texture_amount=0.0, field_amount=1.00,
    speed=0.26, damping=0.996, poke_strength=0.9, poke_radius=0.10,
    breath_rate=0.05, breath_depth=0.18, breath_travel=0.40, drift_depth=0.09,
    level=0.66, ripple_boost=1.55,
    ramp=ramps.TREE, ramp_range=(0.16, 0.94),
    gain=1.00, response=0.55,
)

FORECAST = World(
    name="Forecast", subtitle="the next sixteen hours, one hour per floor",
    # The useful one. Every row is an hour ahead -- ground is now, roof is
    # sixteen hours out -- so weather arrives at the top and comes down the
    # building towards the street. Real numbers from the public forecast.
    #
    # This is the answer to "what does this give the building". A landmark that
    # tells a city what the weather is doing is an instrument, not decoration,
    # and it is exactly what the department inside it exists to do.
    substrate_mix=0.0, is_tree=False, texture="forecast", time_scale=1.0,
    texture_amount=0.98, field_amount=0.18,
    speed=0.26, damping=0.996, poke_strength=0.8, poke_radius=0.14,
    breath_rate=0.05, breath_depth=0.10, breath_travel=0.30, drift_depth=0.06,
    level=0.60, ripple_boost=0.55,
    ramp=ramps.FORECAST, ramp_range=(0.16, 0.95),
    gain=0.80, response=0.60,
)

WORLDS = [SOUNDING, AURORA, SEISMIC, RADAR, REEF,
          ATTENTION, STARTLE, MEMORY, DREAM, TREE, FORECAST]

# What the brain in brain.metta calls each of them.
BY_NAME = {w.name.lower(): w for w in WORLDS}


def blend(a: World, b: World, t: float) -> World:
    """
    An in-between world, t of the way from a to b.

    Sliding t from 0 to 1 over a few seconds is the whole transition. Every law
    changes together and gradually, so the building appears to physically become
    the new world rather than switching to it.

    The two text fields and the pattern name cannot be averaged, so they flip at
    the halfway point. The patterns themselves are crossfaded properly in
    run.py, where both can be drawn at once.
    """
    t = max(0.0, min(1.0, t))
    out = {}
    for f in dataclass_fields(World):
        va, vb = getattr(a, f.name), getattr(b, f.name)
        if isinstance(va, np.ndarray):
            out[f.name] = va + (vb - va) * t       # crossfade the whole ramp
        elif isinstance(va, str):
            out[f.name] = vb if t > 0.5 else va
        elif isinstance(va, tuple):
            out[f.name] = tuple(x + (y - x) * t for x, y in zip(va, vb))
        else:
            out[f.name] = va + (vb - va) * t
    return World(**out)
