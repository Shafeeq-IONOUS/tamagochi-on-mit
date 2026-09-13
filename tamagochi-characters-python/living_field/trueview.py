"""
True view.

This is the most valuable file in the project and it has nothing to do with
being clever.

Every other team will judge their work on a laptop where each window is fifty
pixels wide. It will look fantastic. On the actual building, at four hundred
metres, through night air, half of those ideas turn into a grey smudge -- and
nobody finds out until the night of the install.

So this window shows two things at once:

  LEFT   what everyone else sees while they work. Big, crisp, flattering.
  RIGHT  what a person standing on Memorial Drive actually sees. Tiny, blurred,
         glowing, sitting in the dark.

Design using the right-hand view. Present using both. You will be the only team
in the room with evidence, and by showing it you quietly set the standard
everyone else gets judged against.

There are three layouts, and which one you want depends on what you are doing.
Press V to cycle:

  DESIGN   big laptop view, small honest view. For working. The honest view is
           deliberately tiny -- about the angular size of the real building seen
           from across the river when you are sitting at a laptop.

  PRESENT  the honest view is the hero, the flattering one shrinks to an inset.
           Use this in the pitch. The point you are making is that the small
           view is the real one, and burying it in a corner says the opposite.

  PURE     the honest view alone, nothing else on screen. For the moment in the
           demo where you stop explaining and just let them look at it.

Use + and - to resize the honest view to suit the room. Apparent size depends on
how far away your audience is sitting, so a number that is right at a desk is
wrong when it is projected on a wall. The blur scales with it, so it stays
honest at any size.
"""

import os
import numpy as np
import pygame

from gbsim.display import Display, Frame, Color

ROWS, COLS = 17, 9

# How wide the honest view is by default, in pixels, in DESIGN mode.
# Roughly the angular size of the tower from across the river, at desk distance.
TRUE_WIDTH = 170

DESIGN, PRESENT, PURE = 0, 1, 2
MODE_NAMES = {DESIGN: "design", PRESENT: "present", PURE: "pure"}

# Drop a night photograph of the Green Building here and it becomes the
# backdrop for the true view. Hugely more convincing in a pitch than a
# drawn rectangle. Any photo of the tower at night will do.
PHOTO = os.path.join(os.path.dirname(__file__), "assets", "greenbuilding.jpg")


class TrueView(Display):
    """A display you can see honestly. Swap it for the real building driver."""

    def __init__(self, fullscreen=False, mode=DESIGN):
        pygame.init()
        self._fullscreen = fullscreen
        self._win_size = (980, 820)
        self.mode = mode
        self.true_scale = 1.0
        self.label = ""
        self.font = pygame.font.SysFont("Helvetica", 15)
        self.small = pygame.font.SysFont("Helvetica", 12)
        self._build_screen()

    # ---------------------------------------------------------------------
    def _build_screen(self):
        """Work out the layout for this mode, on whatever screen we are on."""
        if self._fullscreen:
            # A borderless window the size of the screen, NOT true fullscreen.
            #
            # They look identical -- no title bar, fills the display -- but real
            # fullscreen on a Mac takes exclusive control of the screen, so you
            # cannot Cmd-Tab away, cannot reach your notes, and cannot get to
            # anything else during a demo. A borderless window behaves like any
            # other window while looking exactly the same.
            info = pygame.display.Info()
            size = (info.current_w, info.current_h)
            os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
            self.screen = pygame.display.set_mode(size, pygame.NOFRAME)
        else:
            os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
            self.screen = pygame.display.set_mode(self._win_size, pygame.RESIZABLE)
        pygame.display.set_caption("Living Field")

        sw, sh = self.screen.get_size()
        usable = sh - 150

        if self.mode == DESIGN:
            # Working layout: the flattering view leads, the honest one is a
            # small reference beside it.
            self.cell = max(4, usable // ROWS)
            self.true_w = int(TRUE_WIDTH * self.true_scale)
            self._layout_pair(sw, sh, big_leads=True)

        elif self.mode == PRESENT:
            # Pitch layout: the honest view is the hero. It gets the height,
            # and the flattering one shrinks to an inset beside it.
            self.true_w = int(usable * (COLS / ROWS) * self.true_scale)
            self.cell = max(3, int(usable * 0.42) // ROWS)
            self._layout_pair(sw, sh, big_leads=False)

        else:  # PURE
            self.true_w = int(usable * (COLS / ROWS) * self.true_scale)
            self.true_h = int(self.true_w * (ROWS / COLS))
            self.cell = 0
            self.big_w = self.big_h = 0
            self.true_x = (sw - self.true_w) // 2
            self.true_y = (sh - self.true_h) // 2
            self.big_x = self.top = 0

        self.backdrop = self._load_backdrop()

    def _layout_pair(self, sw, sh, big_leads):
        """Place the two views side by side, as a pair, centred on screen."""
        self.big_w = COLS * self.cell
        self.big_h = ROWS * self.cell
        self.true_h = int(self.true_w * (ROWS / COLS))

        gap = max(60, sw // 16)
        total = self.big_w + gap + self.true_w
        left = (sw - total) // 2

        if big_leads:
            self.big_x, self.true_x = left, left + self.big_w + gap
        else:
            self.true_x, self.big_x = left, left + self.true_w + gap

        tall = max(self.big_h, self.true_h)
        top = (sh - tall) // 2 + 10
        self.top = top + (tall - self.big_h) // 2
        self.true_y = top + (tall - self.true_h) // 2

    def mode_name(self):
        return MODE_NAMES[self.mode]

    def cycle_mode(self):
        self.mode = (self.mode + 1) % 3
        self._build_screen()

    def scale_true(self, factor):
        """Make the honest view bigger or smaller, to suit the room."""
        self.true_scale = max(0.35, min(3.0, self.true_scale * factor))
        self._build_screen()

    def resize(self, size):
        """The user dragged the window edge. Lay everything out again."""
        self._win_size = (max(520, size[0]), max(460, size[1]))
        if not self._fullscreen:
            self._build_screen()

    def is_fullscreen(self):
        return self._fullscreen

    def toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self._build_screen()

    def _load_backdrop(self):
        """Real photo if you gave us one, otherwise a plausible night sky."""
        w, h = self.true_w + 150, self.true_h + 170
        if os.path.exists(PHOTO):
            try:
                img = pygame.image.load(PHOTO).convert()
                return pygame.transform.smoothscale(img, (w, h))
            except Exception:
                pass
        surf = pygame.Surface((w, h))
        surf.fill((7, 9, 14))
        return surf

    def to_grid(self, pos):
        """
        Turn a mouse click into a position on the building, 0 to 1.

        Lives here because only this file knows where the grid ended up on
        screen. Returns None if the click was somewhere else.
        """
        x, y = pos
        col = (x - self.big_x) / max(self.big_w, 1)
        row = (y - self.top) / max(self.big_h, 1)
        if 0.0 <= col <= 1.0 and 0.0 <= row <= 1.0:
            return row, col
        return None

    # ---------------------------------------------------------------------
    def makeframe(self):
        return Frame()

    def send(self, frame):
        pixels = np.zeros((ROWS, COLS, 3), dtype=np.uint8)
        for r in range(frame.nrows()):
            row = frame.row(r)
            for c in range(frame.ncols()):
                col = row[c]
                pixels[r, c] = (col.r, col.g, col.b)

        self.screen.fill((10, 10, 12))
        if self.mode != PURE:
            self._draw_big(pixels)
        self._draw_true(pixels)
        self._draw_status()
        pygame.display.flip()

    def _draw_status(self):
        """
        Status along the bottom of the SCREEN, not underneath the grid.

        Anchoring it to the grid meant it ran off the edge as soon as the grid
        moved, which it does every time the layout changes.
        """
        if not self.label:
            return
        sw, sh = self.screen.get_size()
        dim = (70, 70, 80) if self.mode == PURE else (150, 150, 160)
        txt = self.small.render(self.label, True, dim)
        self.screen.blit(txt, (max(20, (sw - txt.get_width()) // 2), sh - 34))

    def _draw_big(self, pixels):
        gap = 1 if self.cell > 12 else 0
        for r in range(ROWS):
            for c in range(COLS):
                rect = pygame.Rect(self.big_x + c * self.cell,
                                   self.top + r * self.cell,
                                   self.cell - gap, self.cell - gap)
                pygame.draw.rect(self.screen, tuple(int(v) for v in pixels[r, c]), rect)

        self.screen.blit(self.font.render("laptop view (flattering)", True, (130, 130, 140)),
                         (self.big_x, self.top - 26))


    def _draw_true(self, pixels):
        self.screen.blit(self.backdrop, (self.true_x - 75, self.true_y - 85))

        # The windows, rendered small and then blurred upward. Scaling a tiny
        # image up smoothly is a cheap and surprisingly accurate stand-in for
        # what big diffuse light panels do to your eye at distance.
        tiny = pygame.surfarray.make_surface(np.transpose(pixels, (1, 0, 2)))
        soft = pygame.transform.smoothscale(tiny, (max(self.true_w // 3, 3), max(self.true_h // 3, 3)))
        soft = pygame.transform.smoothscale(soft, (self.true_w, self.true_h))

        # Glow. Light spills past the window frame in real life, and at distance
        # that spill is most of what you actually see.
        glow = pygame.transform.smoothscale(tiny, (10, 18))
        glow = pygame.transform.smoothscale(glow, (self.true_w + 80, self.true_h + 80))
        # Dim the glow before adding it. (set_alpha is ignored by BLEND_ADD,
        # so we darken the pixels themselves instead.)
        glow.fill((70, 70, 70), special_flags=pygame.BLEND_MULT)

        self.screen.blit(glow, (self.true_x - 40, self.true_y - 40), special_flags=pygame.BLEND_ADD)
        self.screen.blit(soft, (self.true_x, self.true_y), special_flags=pygame.BLEND_ADD)

        self.screen.blit(self.font.render("from across the river", True, (150, 150, 160)),
                         (self.true_x, self.true_y - 26))
        self.screen.blit(self.small.render("this is the one that matters", True, (95, 95, 105)),
                         (self.true_x, self.true_y + self.true_h + 12))
