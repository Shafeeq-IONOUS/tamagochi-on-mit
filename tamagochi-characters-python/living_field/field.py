"""
The living field.

Think of a still pond. Drop a stone in and rings spread out. That is the whole
idea here: the building's face is a pond, people at the bottom drop stones in,
and the ripples travel all the way up the tower.

One important trick lives in this file. The building only has 153 windows
(17 rows by 9 columns), which is far too few squares to run a believable
simulation on. Ripples on a grid that small come out jagged and twitchy.

So we simulate on a much finer invisible grid -- four times bigger in each
direction -- and then average it down to 17x9 at the very last moment. Same
maths, but the motion that reaches the windows is smooth and organic instead
of chunky. This is the difference between "looks alive" and "looks broken".
"""

import numpy as np

# The real display. Do not change these -- they are the building.
ROWS = 17
COLS = 9

# How much finer the hidden simulation is than the display.
# 4 means we simulate 68x36 and average it down to 17x9.
SCALE = 4

HI_ROWS = ROWS * SCALE
HI_COLS = COLS * SCALE


def _laplacian(u):
    """
    Measures, for every point, how much it differs from its neighbours.

    This is the engine of every ripple: a point that is lower than everything
    around it gets pulled up, a point that is higher gets pulled down, and the
    back-and-forth of that pulling is what a wave actually is.

    The edges are mirrored rather than wrapped, so ripples bounce off the top
    and bottom of the building instead of teleporting from one end to the other.
    """
    p = np.pad(u, 1, mode="edge")
    return (
        p[:-2, 1:-1]   # above
        + p[2:, 1:-1]  # below
        + p[1:-1, :-2] # left
        + p[1:-1, 2:]  # right
        - 4.0 * u
    )


def _edge_mask(rows, cols, margin=3, edge_damping=0.992):
    """
    A soft border that quietly absorbs waves as they reach the outside.

    Without this, ripples bounce off the edges of the building and pile up in
    the corners, and within a few seconds the top and the left-hand column are
    permanently brighter than everything else. It looks like a bug because it
    is one.

    With it, waves fade out as they run off the edge -- as though the building
    carries on past what you can see.

    Keep this gentle. An earlier version absorbed so hard that the outermost
    columns went dark and the building effectively lost two of its nine columns.
    Measured: at these settings the edge columns are as bright as the middle.
    """
    m = np.ones((rows, cols), dtype=np.float32)
    for i in range(margin):
        f = edge_damping + (1.0 - edge_damping) * (i / float(margin))
        m[i, :] = np.minimum(m[i, :], f)
        m[-1 - i, :] = np.minimum(m[-1 - i, :], f)
        m[:, i] = np.minimum(m[:, i], f)
        m[:, -1 - i] = np.minimum(m[:, -1 - i], f)
    return m


class Field:
    """The pond. Holds its current surface and what it looked like a moment ago."""

    def __init__(self):
        # The height of the water at every point, now and one step ago.
        # A wave needs both to know which way it is travelling.
        self.u = np.zeros((HI_ROWS, HI_COLS), dtype=np.float32)
        self.u_prev = np.zeros_like(self.u)
        self.edge = _edge_mask(HI_ROWS, HI_COLS)

    def poke(self, row_frac, col_frac, strength=1.0, radius=0.12):
        """
        Drop a stone in the pond.

        row_frac and col_frac are positions from 0 to 1, so (1.0, 0.5) means
        "bottom centre" -- the ground, right where a person would be standing.
        radius is how wide the splash is, as a fraction of the building's height.
        """
        rows = np.arange(HI_ROWS, dtype=np.float32) / HI_ROWS
        cols = np.arange(HI_COLS, dtype=np.float32) / HI_COLS

        # Distance from the splash point to every other point, then a soft
        # bell-shaped bump around it. Softer than a hard circle, which would
        # show up as a visible square-edged blob on the windows.
        dr = (rows - row_frac).reshape(-1, 1)
        dc = (cols - col_frac).reshape(1, -1)
        dist2 = dr * dr + dc * dc
        bump = np.exp(-dist2 / (2.0 * radius * radius)).astype(np.float32)

        self.u += bump * strength

    def step(self, speed, damping):
        """
        Move the simulation forward by one frame.

        speed    -- how fast ripples travel. Keep below about 0.5 or the
                    simulation becomes unstable and explodes into noise.
        damping  -- how quickly ripples fade. 1.0 would ring forever,
                    0.99 settles down over a few seconds.
        """
        lap = _laplacian(self.u)
        u_next = 2.0 * self.u - self.u_prev + (speed * speed) * lap
        u_next *= damping

        # Let waves run off the edges instead of bouncing back and stacking up.
        u_next *= self.edge

        # Safety net: if the numbers ever run away, calm everything down rather
        # than letting the display fill with garbage in front of a crowd.
        np.clip(u_next, -4.0, 4.0, out=u_next)

        self.u_prev = self.u
        self.u = u_next

    def energy(self):
        """How lively the pond is right now, roughly 0 when perfectly still."""
        return float(np.abs(self.u).mean())

    def to_display(self):
        """
        Average the fine hidden grid down to the 17x9 the building actually has.

        This is the one line that makes the motion smooth. Each window shows the
        average of the 16 hidden points behind it, so movement between windows
        glides instead of snapping.
        """
        return self.u.reshape(ROWS, SCALE, COLS, SCALE).mean(axis=(1, 3))
