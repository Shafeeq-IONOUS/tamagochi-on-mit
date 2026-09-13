"""
The tree.

Everything else in this project is a field -- a smooth surface of brightness
with no edges anywhere. Fields are the safe choice at this resolution, because
an arbitrary shape drawn on 153 windows turns to mush.

Branching structures are the exception, and it is worth knowing why. A branch
looks the same at every scale: a trunk splitting into limbs looks like a limb
splitting into twigs. So when the display is too coarse to show the twigs, what
is left still reads as a branching thing rather than as a broken picture. That
self-similarity is exactly why dendritic patterns are one of the few kinds of
form that survive a low-resolution facade -- and a tall narrow tower is the
ideal canvas for one.

WHAT MAKES IT WORTH DOING HERE

The first person to touch the building plants the trunk. Everyone after that
grafts a new limb onto the tree that is already there -- so the crowd does not
grow forty separate trees, it grows ONE, together, and it gets more elaborate
with every person. The branches stay all evening.

That detail was not the first design. Letting each person plant their own trunk
filled the bottom third of the facade with a solid block by the seventh person,
because nine columns cannot hold seven trees. One shared tree is both the thing
that fits and the better idea.

It also sways. The Green Building is famous for its wind: I. M. Pei left the
ground floor open because of it, and Calder's Big Sail sits at its foot to
break it. A tree on that facade that did not move in the wind would be missing
the most obvious thing about the site.
"""

import math
import random
import numpy as np

ROWS, COLS, SCALE = 17, 9, 4
HI_ROWS, HI_COLS = ROWS * SCALE, COLS * SCALE     # 68 x 36

# Growth happens on its own clock, not per drawn frame, so the tree grows at
# the same speed however fast the machine is.
STEPS_PER_SECOND = 9.0
STEP_LENGTH = 1.15          # hi-res cells advanced per step

MAX_SEGMENTS = 2200         # what fits before old twigs start dropping
MAX_TIPS = 120


class _Tip:
    """A growing end. It knows where it is, where it is heading, how thick."""
    __slots__ = ("x", "y", "ang", "width", "gen", "since_split", "life", "budget")

    def __init__(self, x, y, ang, width, gen, budget=999):
        self.x, self.y = x, y
        self.ang = ang                  # radians, -pi/2 is straight up
        self.width = width
        self.gen = gen
        self.since_split = 0
        self.life = 0
        self.budget = budget   # steps left before it stops growing


class Tree:
    """A tree grown out of the people who touched the building."""

    def __init__(self, seed=0):
        self._rng = random.Random(seed)
        self._tips = []
        # Each segment: x0, y0, x1, y1, width, born  -- kept forever.
        self._segs = []
        self._field = np.zeros((HI_ROWS, HI_COLS), dtype=np.float32)
        self._dirty = True
        self._carry = 0.0
        self._planted = 0
        self._age = 0        # counts growth steps, used to dim older wood

    # -- someone touched the building -------------------------------------
    def plant(self, row_frac, col_frac, vigour=1.0):
        """
        The crowd grows one tree, not many.

        The first touch of the night plants the trunk at the foot of the
        building. Every touch after that finds a point on the tree that already
        exists and grows a new limb out of it, angled away from wherever it
        attached. So the tree does not get taller with the crowd, it gets
        FULLER -- which is both what a real tree does and the only thing that
        fits on nine columns.
        """
        if len(self._tips) >= MAX_TIPS:
            return
        self._prune()
        rng = self._rng
        self._planted += 1

        if not self._segs:
            x = col_frac * (HI_COLS - 1)
            y = HI_ROWS - 1.5
            ang = -math.pi / 2 + rng.uniform(-0.10, 0.10)
            self._tips.append(_Tip(x, y, ang, 3.1 * (0.8 + 0.3 * vigour), 0, 95))
            return

        # Graft onto the existing tree. Prefer somewhere near where the person
        # actually touched, so standing at one end of the plaza grows that side.
        tx = col_frac * (HI_COLS - 1)
        ty = row_frac * (HI_ROWS - 1)
        best, bestd = None, 1e9
        for i in range(0, len(self._segs), max(1, len(self._segs) // 90)):
            x0, y0, _, _, w, _born = self._segs[i]
            # Bias upward: new limbs come off the upper tree, not the base.
            d = (x0 - tx) ** 2 + 0.25 * (y0 - ty) ** 2 + y0 * 3.0
            if d < bestd:
                bestd, best = d, (x0, y0, w)
        x, y, w = best
        # Away from centre, so the crown opens out instead of crowding.
        out = 1.0 if x > HI_COLS / 2 else -1.0
        ang = -math.pi / 2 + out * rng.uniform(0.45, 1.05)

        # Each new person adds a SHORTER limb than the last. The first touch of
        # the night grows the whole trunk; the fortieth adds a twig.
        #
        # Without this the tree kept growing full-height limbs and the canopy
        # filled into a solid block by about the ninth person -- the same
        # failure as forty separate trunks, just higher up. A tree gets denser
        # and finer as it fills, not taller.
        budget = max(8, int(46 - 3.4 * self._planted))
        self._tips.append(_Tip(x, y, ang, max(1.0, w * 0.68), 1, budget))

    def _prune(self):
        """
        Make room by dropping the oldest twigs, never the trunk.

        Everyone who touches the building has to leave a mark, including the
        hundredth person of the evening. But branches accumulate, and past a
        couple of thousand the facade fills in. So when it is full the tree
        sheds its oldest THIN wood first -- which is what a real tree does, and
        it means the trunk and main limbs from early in the night survive while
        the fine detail turns over.
        """
        if len(self._segs) < MAX_SEGMENTS:
            return
        need = len(self._segs) - int(MAX_SEGMENTS * 0.86)
        thin = sorted((i for i, sg in enumerate(self._segs) if sg[4] < 1.15),
                      key=lambda i: self._segs[i][5])[:need]
        drop = set(thin)
        if len(drop) < need:                       # not enough twigs: oldest go
            for i in sorted(range(len(self._segs)),
                            key=lambda i: self._segs[i][5]):
                if len(drop) >= need:
                    break
                drop.add(i)
        self._segs = [sg for i, sg in enumerate(self._segs) if i not in drop]
        self._dirty = True

    # -- growth -----------------------------------------------------------
    def grow(self, dt):
        """Advance every growing tip. Called from the drawing loop with the
        real elapsed time, so growth is wall-clock, not frame-rate, paced."""
        self._carry += dt * STEPS_PER_SECOND
        steps = int(self._carry)
        if steps <= 0:
            return
        self._carry -= steps
        for _ in range(min(steps, 6)):
            self._step()

    def _step(self):
        if not self._tips:
            return
        rng = self._rng
        born = []
        alive = []
        for tip in self._tips:
            # Wander. The lean random-walks, but is always pulled back towards
            # vertical -- a branch that wanders freely curls up into a scribble.
            tip.ang += rng.gauss(0.0, 0.26)
            # Pulled back towards vertical, but less so higher up -- which is
            # what opens the crown out instead of growing a bundle of poles.
            pull = 0.20 - 0.030 * tip.gen
            tip.ang += (-math.pi / 2 - tip.ang) * max(pull, 0.05)

            nx = tip.x + math.cos(tip.ang) * STEP_LENGTH
            ny = tip.y + math.sin(tip.ang) * STEP_LENGTH

            # Reflect off the sides rather than growing out of the building.
            if nx < 0.5 or nx > HI_COLS - 1.5:
                tip.ang = math.pi - tip.ang
                nx = min(max(nx, 0.5), HI_COLS - 1.5)

            self._segs.append((tip.x, tip.y, nx, ny, tip.width, self._age))
            tip.x, tip.y = nx, ny
            tip.life += 1
            tip.since_split += 1
            tip.budget -= 1

            # Stop at the roof, when too thin to see, or when the tree is full.
            # 0.30 and not higher. Measured: at 0.42 the branches thinned out
            # and died two thirds of the way up, so the top third of a
            # twenty-one storey building stayed empty all night.
            if ny < 1.0 or tip.width < 0.30 or tip.budget <= 0:
                continue

            # Split. More likely the longer it has been since the last one, so
            # branches space out instead of forking in a clump.
            p = 0.055 * tip.since_split * (1.0 - 0.08 * tip.gen)
            if tip.gen < 6 and tip.since_split > 2 and rng.random() < p \
                    and len(self._tips) + len(born) < MAX_TIPS:
                spread = rng.uniform(0.50, 0.95)
                # A thick branch keeps most of its width; the new one is thinner.
                keep = rng.uniform(0.78, 0.88)
                born.append(_Tip(tip.x, tip.y, tip.ang + spread,
                                 tip.width * (1 - keep) + 0.30, tip.gen + 1,
                                 max(8, int(tip.budget * 0.75))))
                tip.ang -= spread * 0.50
                tip.width *= keep
                tip.since_split = 0
            else:
                tip.width *= 0.976      # taper

            alive.append(tip)

        self._age += 1
        self._tips = alive + born
        self._dirty = True

    # -- drawing ----------------------------------------------------------
    def _rasterise(self):
        """
        Draw every branch into the fine grid.

        Only runs when the tree has actually changed, which is a few times a
        second rather than thirty -- the shape is expensive to draw and almost
        never different between one frame and the next.
        """
        f = np.zeros((HI_ROWS, HI_COLS), dtype=np.float32)
        yy, xx = np.mgrid[0:HI_ROWS, 0:HI_COLS].astype(np.float32)
        newest = max(self._age, 1)
        for (x0, y0, x1, y1, w, born) in self._segs:
            # Older wood is dimmer, newest growth glows.
            #
            # This is what stops the tree going solid. Every branch stays
            # forever -- nothing is ever deleted -- but with a whole evening of
            # them the facade filled in completely and the shape was lost.
            # Fading the old wood keeps the entire night present while leaving
            # the last few minutes clearly readable on top of it.
            recency = born / newest
            weight = 0.52 + 0.48 * (recency ** 1.6)
            # Work only in a box around the segment; the rest cannot be touched.
            r0 = max(int(min(y0, y1) - w - 2), 0)
            r1 = min(int(max(y0, y1) + w + 3), HI_ROWS)
            c0 = max(int(min(x0, x1) - w - 2), 0)
            c1 = min(int(max(x0, x1) + w + 3), HI_COLS)
            if r0 >= r1 or c0 >= c1:
                continue
            sy, sx = yy[r0:r1, c0:c1], xx[r0:r1, c0:c1]
            dx, dy = x1 - x0, y1 - y0
            L2 = dx * dx + dy * dy
            if L2 < 1e-9:
                d2 = (sx - x0) ** 2 + (sy - y0) ** 2
            else:
                t = np.clip(((sx - x0) * dx + (sy - y0) * dy) / L2, 0.0, 1.0)
                d2 = (sx - (x0 + t * dx)) ** 2 + (sy - (y0 + t * dy)) ** 2
            f[r0:r1, c0:c1] = np.maximum(
                f[r0:r1, c0:c1],
                weight * np.exp(-d2 / (2.0 * (w * 0.42) ** 2)))
        self._field = f
        self._dirty = False

    def to_display(self, t=0.0, wind=0.35, bias=0.0):
        """
        The tree as a 17 x 9 picture, swaying.

        The sway is a shear: rows near the roof shift further than rows near
        the ground, which is how a real tree moves -- the trunk barely, the
        top a lot. Done at the fine grid and then averaged down, so the motion
        is smooth rather than windows snapping sideways.

        wind and bias come from the actual weather outside when there is a
        reading for it (see weather.py). bias leans the whole tree the way the
        wind is really blowing, so on a gusty night from the west the tree
        genuinely holds over to one side.
        """
        if self._dirty:
            self._rasterise()

        f = self._field

        # Flutter, before the sway.
        #
        # A trunk sways slowly -- about one full lean every twelve seconds --
        # and on its own that is almost invisible at a glance. What actually
        # makes a tree read as alive is the fast shimmer of the thin stuff at
        # the outside, moving several times a second while the trunk barely
        # moves at all. Measured: sway alone gave 2% motion, which is the same
        # as a photograph. Both together is what a tree looks like.
        if wind > 0.01:
            rr = (np.arange(HI_ROWS, dtype=np.float32) / HI_ROWS).reshape(-1, 1)
            cc = (np.arange(HI_COLS, dtype=np.float32) / HI_COLS).reshape(1, -1)
            high = (1.0 - rr) ** 1.4          # twigs are up and out
            # Coarse on purpose. The first version shimmered at about five
            # cycles across the building, which is exactly the spatial detail
            # four hundred metres of night air destroys -- it measured 2%
            # motion, the same as a photograph, because the blur ate all of it.
            #
            # At that distance you do not see leaves flutter. You see GUSTS
            # travel across the crown: big soft patches brightening and dimming
            # as the wind crosses. So the waves are about one across the whole
            # tower, and they move.
            # Measured end to end: 0.75 deep at 1.2 gusts a second reads as
            # 11% motion once blurred to true scale. Calmer than the weather
            # worlds, which sit near 30% -- which is right. A tree should look
            # quieter than an aurora.
            shimmer = (np.sin(2 * math.pi * (1.20 * t + rr * 1.15 + cc * 0.55))
                       + 0.55 * np.sin(2 * math.pi * (0.72 * t - rr * 0.70 + cc * 0.95)))
            f = f * (1.0 + 0.75 * wind * high * shimmer)

        if wind > 0.01:
            heights = 1.0 - (np.arange(HI_ROWS, dtype=np.float32) / HI_ROWS)
            # Two frequencies, so it breathes rather than metronomes.
            amp = (5.0 * math.sin(2 * math.pi * 0.085 * t)
                   + 1.9 * math.sin(2 * math.pi * 0.21 * t + 1.3)) * wind
            # A steady lean on top of the swaying, in the direction the wind is
            # actually coming from.
            amp += 2.4 * bias * wind
            shift = heights ** 1.7 * amp
            out = np.empty_like(f)
            cols = np.arange(HI_COLS, dtype=np.float32)
            for r in range(HI_ROWS):
                out[r] = np.interp(cols - shift[r], cols, f[r],
                                   left=0.0, right=0.0)
            f = out

        small = f.reshape(ROWS, SCALE, COLS, SCALE).mean(axis=(1, 3))
        # Lift the thin outer twigs, which are what the averaging hurts most.
        return (np.power(np.clip(small, 0, 1), 0.62) * 1.55 - 0.42).astype(np.float32)

    # -- the sort of thing you want to say on stage ------------------------
    def stats(self):
        return {"people": self._planted,
                "branches": len(self._segs),
                "growing": len(self._tips)}
