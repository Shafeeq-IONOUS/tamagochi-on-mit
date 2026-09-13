"""
Patterns that belong to this particular building.

The Green Building is not a blank tower. It is MIT's Department of Earth,
Atmospheric and Planetary Sciences, it has a weather radar dome on its roof,
and it is tall and thin. The people inside it study the atmosphere, the oceans,
earthquakes, and other planets.

So rather than decorating it with pleasant abstract physics, these patterns are
the things the building is actually about -- and they happen to suit its shape,
because a tall narrow column is the natural shape for all of them. An
atmospheric sounding is drawn as a vertical profile. An aurora hangs in vertical
curtains. A seismic wave arrives as a front travelling up through rock. A radar
sweeps from a dome on a roof.

Each function returns a 17 x 9 picture of roughly -1 to 1, where 0 means
"nothing here". They are generated four times finer than the display and then
averaged down, the same trick used everywhere else in this project: it is what
stops a diagonal line coming out as a staircase.
"""

import numpy as np

ROWS, COLS, SCALE = 17, 9, 4
HI_ROWS, HI_COLS = ROWS * SCALE, COLS * SCALE

# There are real trees in front of the building. The bottom two rows of windows
# are behind them and cannot be seen from the street or the river, so nothing
# that carries meaning is allowed to live there.
HIDDEN_ROWS = 2

# Position of every point on the hidden fine grid, as 0 to 1.
# Y is 0 at the roof and 1 at the ground.
_Y = (np.arange(HI_ROWS, dtype=np.float32) + 0.5).reshape(-1, 1) / HI_ROWS
_X = (np.arange(HI_COLS, dtype=np.float32) + 0.5).reshape(1, -1) / HI_COLS
_Y = np.repeat(_Y, HI_COLS, axis=1)
_X = np.repeat(_X, HI_ROWS, axis=0)


def _down(hi):
    """Average the fine grid down to the 153 windows that actually exist."""
    return hi.reshape(ROWS, SCALE, COLS, SCALE).mean(axis=(1, 3))


# ---------------------------------------------------------------------------

def none(t, ctx=None):
    """No pattern. The world's character comes entirely from the wave field."""
    return np.zeros((ROWS, COLS), dtype=np.float32)


def sounding(t, ctx=None):
    """
    ATMOSPHERE -- the building as a vertical slice of sky.

    Weather balloons send back a "sounding": a single vertical profile of the
    air above one spot, layer by layer. It is drawn as a tall thin column,
    which is exactly what this building is.

    So: horizontal bands of different depths, drifting slowly upward, mixing
    where they meet. Warm and dense near the ground, thin and cold at the top --
    the way real air actually stacks.
    """
    y = _Y
    v = np.sin(2 * np.pi * (y * 3.1 - t * 0.030))
    v += 0.50 * np.sin(2 * np.pi * (y * 7.3 + t * 0.019))
    v += 0.22 * np.sin(2 * np.pi * (y * 13.0 - t * 0.045))
    # Layers get thinner and fainter with height, like real atmosphere.
    v *= 0.45 + 0.85 * y
    return _down(v / 1.7).astype(np.float32)


def aurora(t, ctx=None):
    """
    AURORA -- vertical curtains that hang and ripple.

    An aurora is not a glow in the sky, it is a set of sheets of light hanging
    vertically, folding slowly like a curtain in a draught. On a display that is
    tall and only nine windows wide, that is close to the ideal subject.

    The folds drift sideways, and the whole curtain is brightest near the top
    where it hangs from, fading towards the ground.
    """
    y, x = _Y, _X
    # Each curtain leans and waves as it descends -- that is the fold.
    lean = 0.16 * np.sin(2 * np.pi * (y * 0.9 + t * 0.055)) \
         + 0.07 * np.sin(2 * np.pi * (y * 2.1 - t * 0.031))
    v = np.sin(2 * np.pi * ((x + lean) * 2.1 + t * 0.021))
    v = np.sign(v) * np.abs(v) ** 0.65          # sharpen into distinct sheets
    v *= 1.15 - 0.85 * y                        # hangs from the top
    return _down(v).astype(np.float32)


def seismic(t, ctx=None):
    """
    SEISMIC -- a wave arriving through rock.

    An earthquake reaches a seismometer in stages: a sharp fast P-wave first,
    then a slower, larger S-wave behind it, then a long ragged tail called the
    coda. In between, the trace is almost flat.

    That shape is dramatic on a building: long calm, then a hard bright front
    that climbs the tower, then a slow untidy decay.
    """
    period = 17.0
    phase = (t % period) / period

    front = 1.12 - phase * 1.55                 # travels ground -> roof
    d = _Y - front

    p_wave = np.exp(-(d * d) / (2 * 0.030 ** 2))
    s_wave = 0.75 * np.exp(-((d - 0.155) ** 2) / (2 * 0.085 ** 2))
    coda = 0.30 * np.exp(-np.clip(d - 0.28, 0, 9) / 0.35) \
                * np.sin(2 * np.pi * (_Y * 9.0 - t * 1.1))

    quiet = 0.06 * np.sin(2 * np.pi * (_Y * 2.0 + t * 0.08))
    v = p_wave + s_wave + coda + quiet
    return _down(v * 1.5 - 0.28).astype(np.float32)


def radar(t, ctx=None):
    """
    RADAR -- the dome on the roof, sweeping.

    There is a weather radar radome on top of this building. This is its beam,
    seen head on: a sector scan swinging back and forth from the roof, with the
    echo fading behind it the way it does on a real radar screen.

    The beam comes from the top centre, because that is where the dome is.
    """
    period = 9.0
    swing = np.sin(2 * np.pi * t / period)
    ang = swing * 1.10                           # about +/- 63 degrees
    going_right = np.cos(2 * np.pi * t / period) > 0

    dx = _X - 0.5
    dy = _Y + 0.03                               # origin sits on the roof
    a = np.arctan2(dx, dy)
    da = a - ang

    beam = np.exp(-(da * da) / (2 * 0.13 ** 2))
    # The echo lingers on the side the beam has already passed.
    behind = da if going_right else -da
    trail = 0.55 * np.exp(-np.clip(behind, 0, 9) / 0.42)

    dist = np.sqrt(dx * dx + dy * dy)
    v = (beam + trail) * (0.40 + 0.80 * dist)
    return _down(v * 1.7 - 0.38).astype(np.float32)


PATTERNS = {
    "none": none,
    "sounding": sounding,
    "aurora": aurora,
    "seismic": seismic,
    "radar": radar,
}


# ===========================================================================
#  The four behaviours that need to know about people.
#
#  Everything above is weather -- it runs the same whether anyone is there or
#  not. These four take `ctx`, which carries where the building's attention is
#  and what it remembers, and they are the reason this is an embodied piece
#  rather than an animation.
# ===========================================================================

def _focus(ctx, default=(0.92, 0.5)):
    """Where the building is paying attention, as (row, col) from 0 to 1."""
    if ctx and ctx.get("focus"):
        return ctx["focus"]
    return default


def attention(t, ctx=None):
    """
    IT HAS NOTICED YOU.

    Light gathers towards the person and the whole field tilts that way. From
    the ground this reads as the tower leaning down to look at you, which is
    the single most legible thing a tall building can do -- because where the
    light sits, high or low, is one of the only things that survives four
    hundred metres of night air.

    It breathes while it watches. A held stare that does not move at all reads
    as a machine; a stare that drifts slightly reads as alive.
    """
    fr, fc = _focus(ctx)
    intensity = 0.55 + 0.45 * float((ctx or {}).get("intensity", 0.6))

    # A wander, so the gaze settles rather than snapping -- and so it is
    # visibly alive. The first version moved by two percent of the building
    # every eleven seconds, which measured 3% motion: a staring photograph.
    # A real gaze drifts, and the drift is most of what makes being looked at
    # feel like being looked at by something.
    fr = fr + 0.055 * np.sin(2 * np.pi * t * 0.23) + 0.02 * np.sin(2 * np.pi * t * 0.51)
    fc = fc + 0.085 * np.sin(2 * np.pi * t * 0.17 + 1.1) + 0.03 * np.sin(2 * np.pi * t * 0.43)

    dr, dc = _Y - fr, _X - fc
    near = np.exp(-(dr * dr / (2 * 0.30 ** 2) + dc * dc / (2 * 0.26 ** 2)))

    # A brighter core, so there is something to meet your eye.
    pupil = np.exp(-(dr * dr / (2 * 0.10 ** 2) + dc * dc / (2 * 0.11 ** 2)))

    breathe = 1.0 + 0.22 * np.sin(2 * np.pi * t * 0.42)
    v = (0.85 * near + 0.75 * pupil) * breathe * intensity
    return _down(v * 1.02 - 0.30).astype(np.float32)


def startle(t, ctx=None):
    """
    IT FLINCHED.

    A hard bright flash at the point of contact, then the light RECOILS -- a
    dark ring races outward and the building pulls back, before easing home.

    Recoil is the thing. Everything else in this project gets brighter when
    touched. Something alive does not simply brighten when startled, it moves
    away first, and that half second of withdrawal is what makes a person say
    "it reacted to me" instead of "it lit up".
    """
    fr, fc = _focus(ctx)
    age = float((ctx or {}).get("age", 0.0))      # seconds since the contact

    # The held gaze drifts a little, the way a held gaze does.
    fr = fr + 0.08 * np.sin(2 * np.pi * 0.31 * t)
    fc = fc + 0.08 * np.sin(2 * np.pi * 0.23 * t + 1.0)

    dr, dc = _Y - fr, _X - fc
    dist = np.sqrt(dr * dr + dc * dc)

    hit = np.exp(-age / 0.22) * np.exp(-(dist * dist) / (2 * 0.12 ** 2))

    # The shock front, travelling outward and thinning as it goes.
    radius = age * 0.85
    ring = np.exp(-((dist - radius) ** 2) / (2 * (0.06 + 0.05 * age) ** 2))
    ring *= np.exp(-age / 0.9)

    # Behind the front, the building is darker than its resting state. This is
    # the withdrawal, and it is why the effect reads as a flinch.
    pulled_back = -0.55 * np.exp(-age / 1.3) * np.clip(1.0 - dist / max(radius, 1e-3), 0, 1)

    settle = 1.0 - np.exp(-age / 2.2)             # easing back to normal

    # What it does AFTER the flinch, which matters more than the flinch itself.
    #
    # This used to settle to a flat dim field, so four seconds of recoil were
    # followed by ten seconds of blank wall -- because the world stays chosen
    # until the creature calms down, which takes far longer than the flinch.
    # Measured, that read as 2% motion: a still photograph of a startled
    # building.
    #
    # Something that has just been startled does not go blank. It watches. So
    # it settles into a held, breathing glow around whatever startled it, with
    # its attention still on the spot.
    watch = np.exp(-(dist * dist) / (2.0 * 0.34 ** 2))
    watch *= 0.30 + 0.26 * np.sin(2 * np.pi * 1.10 * t)
    # Measured at 8% motion, which is the quietest state in the piece and
    # deliberately so: a creature holding its attention on you is not supposed
    # to be busy. It is supposed to be still, and breathing.
    alert = 0.16 + 0.9 * watch

    v = (1.35 * hit + 1.05 * ring + pulled_back) * (1.0 - settle) + alert * settle
    return _down(np.clip(v, -1.2, 1.2) - 0.10).astype(np.float32)


def memory(t, ctx=None):
    """
    EVERYONE WHO TOUCHED IT TONIGHT.

    Every contact leaves a mark, and the marks stay. Older ones spread wider
    and dim; newer ones are small and sharp. By the end of an evening the
    pattern on the building is not a design -- it is a record of the people who
    stood at its foot.

    This is the piece. Everything else the building does resets. This does not.
    """
    touches = (ctx or {}).get("touches") or []
    now = (ctx or {}).get("now", t)

    v = np.zeros_like(_Y)
    if not touches:
        # Nobody yet. A faint waiting pulse, so it never looks switched off.
        return _down(0.22 * np.sin(2 * np.pi * (_Y * 1.4 - t * 0.05)) - 0.08).astype(np.float32)

    for (tt, r, c, w) in touches[-220:]:
        age = max(0.0, now - tt)
        # A mark spreads as it ages, the way a memory becomes less exact.
        # Kept SMALL on purpose. An earlier version used marks three times this
        # wide and they merged into a single white sheet within about twenty
        # touches -- measured, every window identical. The whole point of this
        # world is that you can pick out individual people, so the marks have
        # to stay smaller than the gaps between them.
        # A mark must be at least one window wide or it disappears when the
        # fine grid is averaged down to the 153 real windows. Measured: at half
        # this size the first visitor of the night left a mark of 0.04 -- which
        # is nothing.
        radius = 0.070 + 0.012 * np.sqrt(age)
        # ...and fades, but never all the way to nothing within an evening.
        strength = w * (0.25 + 0.75 * np.exp(-age / 420.0))
        dr, dc = _Y - r, _X - c
        v += strength * np.exp(-(dr * dr + dc * dc) / (2 * radius * radius))

    # Breathing over the whole record, so it is a living thing rather than a
    # photograph of one.
    #
    # The first version drifted at 0.08 Hz across two and a bit cycles of the
    # building, and measured 1% motion -- indistinguishable from a still image.
    # Two things were wrong: far too slow, and the pattern was fine enough that
    # the distance blur removed most of what movement there was. Slower waves
    # that actually move is what reads: light travelling through the record,
    # like something passing over it.
    v *= (1.0 + 0.34 * np.sin(2 * np.pi * (0.95 * t + _Y * 1.1 + _X * 0.6))
              + 0.16 * np.sin(2 * np.pi * (0.55 * t - _Y * 0.8)))

    # Crowded places glow brighter, and keep getting brighter.
    #
    # This is the hardest number in the project to get right, because it has to
    # hold forty times the range in accumulated marks inside about three times
    # the range in brightness. An earlier version squashed with tanh, which
    # flattened everything above a certain crowd size to exactly the same value
    # -- twenty people in a spot looked identical to five. This curve is
    # normalised rather than offset, so it keeps rising all the way.
    #
    # Measured, end to end: one visitor 0.40, five 0.58, fifteen 0.77,
    # forty 0.92. The building visibly fills up over an evening.
    v = np.log1p(10.0 * v) / np.log1p(10.0 * 22.0)
    # Pulled down from the top of the range. At full strength 59% of the
    # windows sat at the brightness cap, which throws away every distinction
    # between a busy corner and a very busy one.
    return _down(np.clip(v * 0.86, -1.0, 1.02)).astype(np.float32)


def dream(t, ctx=None):
    """
    IT IS REPLAYING THE EVENING.

    When nobody has been near for a long time and it is tired, the building
    goes back over the night at speed -- each person who touched it flaring
    again in the order they arrived, minutes compressed into seconds.

    A person watching a replay of a crowd they were part of tends to stay and
    watch for the bit where they appear.
    """
    touches = (ctx or {}).get("touches") or []
    if not touches:
        y = _Y
        v = np.sin(2 * np.pi * (y * 1.8 - t * 0.06)) * (0.5 + 0.5 * y)
        return _down(v * 0.8).astype(np.float32)

    t0, t1 = touches[0][0], touches[-1][0]
    span = max(t1 - t0, 1.0)
    cycle = 22.0                                   # one replay of the night
    head = ((t % cycle) / cycle) * span + t0       # where the replay is now

    v = np.zeros_like(_Y)
    for (tt, r, c, w) in touches[-220:]:
        d = head - tt
        if d < -0.4 * span or d > 0.30 * span:
            continue
        # Bright as the replay passes over it, then a long tail behind.
        amp = np.exp(-abs(d) / (0.035 * span)) + 0.30 * np.exp(-max(d, 0) / (0.16 * span))
        dr, dc = _Y - r, _X - c
        v += w * amp * np.exp(-(dr * dr + dc * dc) / (2 * 0.075 ** 2))

    # A soft band marking where in the evening the replay has reached.
    pos = (head - t0) / span
    v += 0.30 * np.exp(-((_Y - pos) ** 2) / (2 * 0.10 ** 2))

    v = np.tanh(v * 1.1)
    return _down(v * 1.28 - 0.30).astype(np.float32)


PATTERNS.update({
    "attention": attention,
    "startle": startle,
    "memory": memory,
    "dream": dream,
})


def forecast(t, ctx=None):
    """
    THE BUILDING TELLS YOU THE WEATHER.

    This is the one that is useful rather than beautiful, and it is the reason
    a facade like this can be worth more to a building than decoration.

    Every row is one hour ahead. The ground is now; the roof is sixteen hours
    from now. Rain shows bright, cloud shows dim, clear shows dark. So a front
    arriving appears at the top of the tower and DESCENDS towards the street
    over the hours before it reaches you.

    Somebody across the river learns to read it once -- bright band coming down
    the building means rain is coming -- and after that they always know. That
    is the department of atmospheric science doing its actual job, in public,
    at the scale of a landmark.

    Real numbers, from the public forecast for this grid square. If there is no
    forecast it shows a calm neutral column rather than making anything up.
    """
    rows = (ctx or {}).get("forecast")
    if not rows:
        y = _Y
        return _down(0.25 * np.sin(2 * np.pi * (y * 1.3 - t * 0.04)) - 0.05).astype(np.float32)

    # The bottom two rows are behind the real tree line and nobody can see
    # them. "Now" is the anchor of the whole reading -- if it is hidden, the
    # scale has no bottom and the display means nothing. So the hours are
    # compressed into the rows that are actually visible, and now sits just
    # above the trees.
    visible = ROWS - HIDDEN_ROWS
    col = np.zeros((ROWS, 1), dtype=np.float32)
    for i in range(visible):
        # rows[] is roof-first, so walk it proportionally into the visible part
        src = int(round(i * (len(rows) - 1) / max(visible - 1, 1)))
        rain, cloud = rows[min(src, len(rows) - 1)]
        col[i, 0] = min(1.0, 0.30 * cloud + 1.05 * rain)
    # Behind the trees: carry the nearest visible value so nothing has an edge.
    for i in range(visible, ROWS):
        col[i, 0] = col[visible - 1, 0]

    # Smear each hour across the fine grid, then let the weather drift
    # sideways -- real fronts move, and a column of flat bars looks like a
    # chart rather than a sky.
    band = np.repeat(np.repeat(col, SCALE, axis=0), HI_COLS, axis=1)
    drift = 0.16 * np.sin(2 * np.pi * (0.035 * t + _Y * 0.8))
    v = band * (1.0 + drift) + 0.05 * np.sin(2 * np.pi * (0.06 * t + _X * 0.9 + _Y * 1.4))
    return _down(v * 1.75 - 0.55).astype(np.float32)


PATTERNS["forecast"] = forecast
