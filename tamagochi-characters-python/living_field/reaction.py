"""
Reaction-diffusion -- the building grows its own skin.

This is the maths behind leopard spots, zebra stripes, seashell markings and
coral. Alan Turing worked it out in 1952, in his last published paper, trying to
explain how an animal that starts as a featureless ball of cells ends up with
a pattern on it.

The idea is almost silly in how simple it is. Imagine two chemicals soaking
through a surface:

  A  is food. It sits there and slowly gets topped up.
  B  eats A. Wherever B meets A, it consumes it and makes more of itself.

Both spread out, but B spreads more slowly than A. That single difference --
one thing spreading slower than the other -- is enough. Blobs form. They grow,
they push against each other, they split in two, they leave gaps. Forever.
Nobody is drawing them.

Why this matters for a building: it is *self-sustaining*. The wave field in
field.py fades out and has to be topped up with fake ripples on a timer. This
never needs anything. Left alone for six hours it is still moving, still
changing, and never repeats. A building that is genuinely never still cannot
look broken.
"""

import numpy as np

ROWS = 17
COLS = 9
SCALE = 4
HI_ROWS = ROWS * SCALE     # 68
HI_COLS = COLS * SCALE     # 36


def _lap(x):
    """
    How much each point differs from its neighbours -- the 'spreading out' bit.

    Uses the diagonal neighbours too, at lower weight. Without them the patterns
    come out looking square, because the maths can only spread up/down/left and
    right and the grid itself starts showing through.
    """
    p = np.pad(x, 1, mode="edge")
    return (
        0.20 * (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:])
        + 0.05 * (p[:-2, :-2] + p[:-2, 2:] + p[2:, :-2] + p[2:, 2:])
        - x
    )


class ReactionField:
    """
    The living skin.

    Same three methods as the wave field -- poke, step, to_display -- so the
    rest of the programme cannot tell them apart.
    """

    # How fast each chemical spreads. B MUST be slower than A. If they spread
    # at the same rate nothing happens at all, and the screen stays blank.
    DIFFUSE_A = 0.20
    DIFFUSE_B = 0.09

    # feed  -- how fast A is topped up
    # kill  -- how fast B is removed
    # These two numbers decide what the pattern looks like, and they are
    # touchy. Small changes give spots, stripes, mazes, or nothing at all.
    # These settle into big soft blobs that drift and divide, which is what
    # survives being shrunk to 153 windows.
    # Measured: the textbook 'coral' numbers (0.0545 / 0.0620) settle into a
    # still photograph within twenty seconds and never move again -- a beautiful
    # pattern that is completely dead. These are from the chaotic regime, where
    # blobs keep dividing and drifting and the surface never repeats.
    FEED = 0.0260
    KILL = 0.0510

    # Steps of chemistry per displayed frame. Patterns take thousands of steps
    # to develop, so at one step per frame you would watch nothing happen for
    # several minutes. Four is the pace that reads as alive without looking
    # agitated -- measured at 14% change per third of a second.
    STEPS_PER_FRAME = 4

    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        self.a = np.ones((HI_ROWS, HI_COLS), dtype=np.float32)
        self.b = np.zeros((HI_ROWS, HI_COLS), dtype=np.float32)

        # Sprinkle a few starting colonies. Without a seed the whole thing is
        # perfectly even, and a perfectly even surface never changes -- there
        # is nothing for a pattern to grow out of.
        for _ in range(9):
            r = rng.integers(6, HI_ROWS - 6)
            c = rng.integers(4, HI_COLS - 4)
            self.b[r - 3:r + 3, c - 3:c + 3] = 1.0
            self.a[r - 3:r + 3, c - 3:c + 3] = 0.0

    def poke(self, row_frac, col_frac, strength=1.0, radius=0.12):
        """
        Somebody touched the building, so life starts growing there.

        Rather than a ripple, this plants a new colony. It takes hold, spreads
        outward, and keeps going long after the person has walked away -- which
        is a much better thing for a building to do with a touch than simply
        flashing.
        """
        rows = np.arange(HI_ROWS, dtype=np.float32) / HI_ROWS
        cols = np.arange(HI_COLS, dtype=np.float32) / HI_COLS
        dr = (rows - row_frac).reshape(-1, 1)
        dc = (cols - col_frac).reshape(1, -1)
        bump = np.exp(-(dr * dr + dc * dc) / (2.0 * radius * radius)).astype(np.float32)
        seed = np.clip(bump * strength, 0.0, 1.0)
        self.b = np.clip(self.b + seed, 0.0, 1.0)
        self.a = np.clip(self.a - seed * 0.7, 0.0, 1.0)

    def step(self, speed=None, damping=None):
        """
        Run the chemistry forward one displayed frame.

        speed and damping are ignored -- they only exist so this can be dropped
        in wherever the wave field is used.
        """
        for _ in range(self.STEPS_PER_FRAME):
            a, b = self.a, self.b
            reaction = a * b * b
            self.a = np.clip(a + (self.DIFFUSE_A * _lap(a) - reaction
                                  + self.FEED * (1.0 - a)), 0.0, 1.0)
            self.b = np.clip(b + (self.DIFFUSE_B * _lap(b) + reaction
                                  - (self.KILL + self.FEED) * b), 0.0, 1.0)

    def energy(self):
        return float(self.b.mean())

    def to_display(self):
        """
        Average down to 17 x 9, and centre it around zero.

        The rest of the programme expects roughly -1 to 1, where 0 is 'nothing
        happening', so B gets shifted and stretched to match. That way the same
        colour code works for both kinds of field.
        """
        small = self.b.reshape(ROWS, SCALE, COLS, SCALE).mean(axis=(1, 3))
        return (small - 0.18) * 4.5
