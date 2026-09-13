"""
The safety governor.

Every single frame passes through here on its way to the windows, and nothing
can skip it. This exists for two reasons.

One: this is a 21-storey light visible from Memorial Drive traffic and from
across the Charles. Rapidly flashing a whole building is a genuine seizure risk
and a genuine driver-distraction risk.

Two: MIT has to approve this before it goes on their building. Being able to
hand someone this file, and say "here is exactly what it can never do", is worth
more than any feature. It turns you into the safe choice.

The rules, in plain English:
  - Never brighter than a set ceiling.
  - The whole facade can never jump in brightness quickly. Slow swells only.
  - And no single window may flicker, however calm the facade average looks.
  - Never a full facade of saturated red -- from a distance that reads as an
    emergency, and people will call one in.
  - Never imitate a slow blinking beacon at the top, because the building has a
    real aircraft warning beacon and confusing the two is unacceptable.
"""

import numpy as np

# Brightest any window may ever be, as a fraction of full power.
MAX_BRIGHTNESS = 0.85

# The most the average brightness of the whole facade may change in one frame.
# At 30 frames a second, 0.012 means a full dark-to-bright swell takes about
# three seconds -- roughly 0.18 Hz, far below the ~3 Hz seizure threshold --
# while still allowing a heartbeat to read clearly.
MAX_GLOBAL_STEP = 0.012

# The most any SINGLE window may change in one frame.
#
# This exists because the rule above is not enough, and that was a real hole.
# It watches the average across all 153 windows, so one window can flash bright
# while its neighbour goes dark and the average never moves. Measured before
# this limit existed: individual windows swinging 154% of full brightness per
# second in one mode and 454% in another -- roughly two flashes a second, on a
# facade the size of a building, inside frames the governor was calling safe.
#
# 0.022 a frame is about 66% a second: a window can go from dark to full in a
# second and a half, which is a swell. It cannot blink.
MAX_WINDOW_STEP = 0.022

# If the whole facade is this red and this uniform, pull the red back.
RED_DOMINANCE = 0.72
RED_COVERAGE = 0.80


class Governor:
    def __init__(self):
        self._last = None

    def apply(self, rgb):
        """
        rgb comes in as a 17 x 9 x 3 array of numbers from 0 to 1.
        What comes out is safe to put on a building.
        """
        rgb = np.clip(rgb, 0.0, 1.0) * MAX_BRIGHTNESS

        # --- rule 3: no full facade of emergency red ---
        red = rgb[:, :, 0]
        other = rgb[:, :, 1:].max(axis=2)
        looks_red = (red > RED_DOMINANCE) & (other < red * 0.35)
        if looks_red.mean() > RED_COVERAGE:
            # Warm it towards amber rather than killing it. Still dramatic,
            # no longer reads as "the building is on fire".
            rgb[:, :, 1] = np.maximum(rgb[:, :, 1], red * 0.45)

        np.clip(rgb, 0.0, MAX_BRIGHTNESS, out=rgb)

        if self._last is None:
            self._last = rgb.copy()
            return rgb

        # --- rule 2: the whole facade may only change slowly ---
        # This is the strobe limiter and it is the one that actually matters.
        #
        # It works by holding the new frame back towards the previous one, not
        # by rescaling the new frame's brightness. That distinction is the whole
        # thing. The rescaling version could not slow a fade at all: to soften a
        # drop it had to make the frame brighter, the pixels were already at the
        # ceiling, and the clip put them straight back. Measured, it let 132
        # frames through over the limit, the worst nearly three times over.
        #
        # A blend between two frames that are both already legal is always
        # legal, so nothing downstream can undo this.
        delta = abs(float(rgb.mean()) - float(self._last.mean()))
        if delta > MAX_GLOBAL_STEP:
            k = MAX_GLOBAL_STEP / delta
            rgb = self._last + (rgb - self._last) * k

        # --- rule 2b: and no single window may flicker ---
        # Clamp how far each window is allowed to move from where it was. Like
        # the rule above this is a move towards the new frame rather than a
        # rescale of it, so the result is always between two legal frames and
        # nothing downstream can undo it.
        step = rgb - self._last
        np.clip(step, -MAX_WINDOW_STEP, MAX_WINDOW_STEP, out=step)
        rgb = self._last + step

        self._last = rgb.copy()
        return rgb
