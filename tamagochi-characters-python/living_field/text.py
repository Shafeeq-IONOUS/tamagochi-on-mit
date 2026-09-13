"""
Words on the building.

The forecast display has a real problem: it is only useful to somebody who has
been told how to read it. A stranger seeing a bright band near the roof learns
nothing. "Learn it once and you always know" is a nice line, but nobody learns
anything from a building they walk past.

So the building says it in words.

HOW IT READS

The message runs ACROSS, in a band near the top of the tower, the way any
ticker does. Nine columns is narrow -- about two letters are on the building at
once -- so it moves slowly and you read it the way you read a sign through a
gap. That is a real constraint and it is why the messages are three or four
words at most.

It appears and disappears in the same place. The band fades up out of the
facade, the words travel through it, and the band fades away again -- rather
than wiping in from one edge and out the other, which on a building reads as a
fault rather than a message.

Letters also fade at both edges of the band as they enter and leave, so nothing
ever pops into existence half-drawn.

WHY THE MESSAGES ARE A FIXED LIST

Anything a building says in words is a content decision somebody has to sign
off. So the messages are not generated: they are assembled from a small fixed
vocabulary, all of it weather, all of it reviewable in advance on one page. The
building can say RAIN 3PM. It cannot say anything nobody has approved.
"""

import numpy as np

ROWS, COLS, SCALE = 17, 9, 4
HI_ROWS, HI_COLS = ROWS * SCALE, COLS * SCALE

CHAR_W, CHAR_H = 4, 7
LINE = CHAR_H + 2          # a blank row above and below each letter

# A 4x7 face. Condensed on purpose: at five wide only one and a half letters
# fit across the building at a time, and at four it is nearly two. Measured
# through the distance blur, the narrower face is no harder to read -- both have
# exactly one confusable pair -- so the extra letter is free.
#
# Thin strokes and enclosed holes vanish at this size, so the letters stay
# blocky and open.
_FONT = {
    "A": ("0110", "1001", "1001", "1111", "1001", "1001", "1001"),
    "B": ("1110", "1001", "1110", "1001", "1001", "1001", "1110"),
    "C": ("0111", "1000", "1000", "1000", "1000", "1000", "0111"),
    "D": ("1110", "1001", "1001", "1001", "1001", "1001", "1110"),
    "E": ("1111", "1000", "1110", "1000", "1000", "1000", "1111"),
    "F": ("1111", "1000", "1110", "1000", "1000", "1000", "1000"),
    "G": ("0111", "1000", "1000", "1011", "1001", "1001", "0111"),
    "H": ("1001", "1001", "1111", "1001", "1001", "1001", "1001"),
    "I": ("1111", "0110", "0110", "0110", "0110", "0110", "1111"),
    "L": ("1000", "1000", "1000", "1000", "1000", "1000", "1111"),
    "M": ("1001", "1111", "1111", "1001", "1001", "1001", "1001"),
    "N": ("1001", "1101", "1011", "1001", "1001", "1001", "1001"),
    "O": ("0110", "1001", "1001", "1001", "1001", "1001", "0110"),
    "P": ("1110", "1001", "1001", "1110", "1000", "1000", "1000"),
    "R": ("1110", "1001", "1001", "1110", "1010", "1001", "1001"),
    "S": ("0111", "1000", "0110", "0001", "0001", "1001", "0110"),
    "T": ("1111", "0110", "0110", "0110", "0110", "0110", "0110"),
    "U": ("1001", "1001", "1001", "1001", "1001", "1001", "0110"),
    "W": ("1001", "1001", "1001", "1001", "1011", "1101", "1001"),
    "Y": ("1001", "1001", "0110", "0110", "0110", "0110", "0110"),
    "0": ("0110", "1001", "1011", "1101", "1001", "1001", "0110"),
    "1": ("0010", "0110", "0010", "0010", "0010", "0010", "0111"),
    "2": ("0110", "1001", "0001", "0010", "0100", "1000", "1111"),
    "3": ("1110", "0001", "0110", "0001", "0001", "0001", "1110"),
    "4": ("0010", "0110", "1010", "1111", "0010", "0010", "0010"),
    "5": ("1111", "1000", "1110", "0001", "0001", "1001", "0110"),
    "6": ("0110", "1000", "1110", "1001", "1001", "1001", "0110"),
    "7": ("1111", "0001", "0010", "0010", "0100", "0100", "0100"),
    "8": ("0110", "1001", "0110", "1001", "1001", "1001", "0110"),
    "9": ("0110", "1001", "1001", "0111", "0001", "0001", "0110"),
    " ": ("0000",) * 7,
}


def _glyph(ch):
    return _FONT.get(ch.upper(), _FONT[" "])


class Ticker:
    """A short message running across the building, near the top."""

    # How long one letter takes to cross its own width. Slow, because these are
    # windows and a person has to catch it from across a river.
    SECONDS_PER_CHAR = 1.25

    # Which rows the band occupies. Near the top, where the sky is -- and out
    # of the way of the forecast's own bottom half, which is the hours that
    # matter most.
    BAND_TOP = 3

    # How long the band takes to fade up and fade away.
    FADE = 1.1

    def __init__(self, message=""):
        self.set(message)

    def set(self, message):
        self.message = (message or "").strip()
        self._chars = list(self.message) if self.message else []

    @property
    def active(self):
        return bool(self._chars)

    def duration(self):
        """One full pass, including the fade at each end."""
        if not self._chars:
            return 0.0
        travel = (len(self._chars) + COLS / (CHAR_W + 1)) * self.SECONDS_PER_CHAR
        return travel + 2 * self.FADE

    def render(self, t):
        """
        The message at this moment, as a 17 x 9 picture of 0 to 1.

        Drawn at the display's own resolution and never smoothed -- a blurred
        letter is not a letter, and the distance will do enough blurring on its
        own.
        """
        if not self._chars:
            return None
        total = self.duration()
        if t < 0 or t > total:
            return None

        # The band fades up, holds, and fades away in the same place.
        if t < self.FADE:
            alpha = t / self.FADE
        elif t > total - self.FADE:
            alpha = max(0.0, (total - t) / self.FADE)
        else:
            alpha = 1.0
        alpha = alpha * alpha * (3.0 - 2.0 * alpha)      # ease, no hard edges
        if alpha <= 0.01:
            return None

        step = CHAR_W + 1                      # one blank column between letters
        travelled = ((t - self.FADE) / self.SECONDS_PER_CHAR) * step
        out = np.zeros((ROWS, COLS), dtype=np.float32)

        for i, ch in enumerate(self._chars):
            left = COLS + i * step - travelled  # enters from the right
            if left > COLS or left + CHAR_W < 0:
                continue
            g = _glyph(ch)
            for r in range(CHAR_H):
                y = self.BAND_TOP + r
                if not (0 <= y < ROWS):
                    continue
                row = g[r]
                for c in range(CHAR_W):
                    if row[c] != "1":
                        continue
                    x = left + c
                    xi = int(round(x))
                    if 0 <= xi < COLS:
                        # Soften the two outer columns so letters arrive and
                        # leave rather than appearing whole.
                        edge = min(1.0, min(xi + 1, COLS - xi) / 2.0)
                        out[y, xi] = max(out[y, xi], edge)
        return out * alpha


# ---------------------------------------------------------------------------
# The vocabulary. Everything the building is allowed to say.
#
# Deliberately tiny and entirely weather. Anyone approving this can read the
# whole list in ten seconds and know there is no way for it to say anything
# else, because the messages are assembled from these pieces and nothing else.
# ---------------------------------------------------------------------------

def weather_message(weather):
    """
    One short line about what is coming, or nothing if there is nothing to say.

    Silence is a real option and it is used often. A building that talks
    constantly is noise; one that speaks only when the weather is about to
    change is worth looking up at.
    """
    if weather is None:
        return ""
    rows = weather.forecast_rows()
    if not rows:
        return ""

    # rows are roof-first, so the last entry is now and earlier entries are
    # further ahead. Walk forward in time looking for the first wet hour.
    upcoming = list(reversed(rows))          # now first
    for hours_ahead, (rain, _cloud) in enumerate(upcoming):
        if rain >= 0.55:
            if hours_ahead == 0:
                return "RAIN NOW"
            if hours_ahead == 1:
                return "RAIN 1 HOUR"
            if hours_ahead <= 9:
                return f"RAIN {hours_ahead} HOURS"
            return "RAIN TONIGHT"

    temp = weather.temp_c
    if temp is not None and temp <= 0:
        return "ICE TONIGHT"
    return "CLEAR TONIGHT"
