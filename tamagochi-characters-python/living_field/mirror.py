"""
Draw the same frames in two places at once.

During a demo you want the building on the projector and a window on the laptop
you can actually click. Both take the same seventeen-by-nine frames, so nothing
in the renderer needs to know there are two of them.

The local window comes first in the list and owns the keyboard and mouse; the
others just receive pictures.
"""

from gbsim.display import Display, Frame


class Mirror(Display):
    """One display that is really several. The first one is the interactive one."""

    def __init__(self, primary, *others):
        self.primary = primary
        self.others = list(others)
        self.label = ""

    def makeframe(self):
        return Frame()

    def send(self, frame):
        self.primary.label = self.label
        self.primary.send(frame)
        for d in self.others:
            try:
                d.send(frame)
            except Exception:
                # A simulator going quiet must never take the building with it.
                pass

    def close(self):
        for d in [self.primary] + self.others:
            if hasattr(d, "close"):
                try:
                    d.close()
                except Exception:
                    pass

    # the local window owns interaction; pass everything through to it
    def to_grid(self, pos):
        return self.primary.to_grid(pos)

    def is_fullscreen(self):
        return self.primary.is_fullscreen()

    def toggle_fullscreen(self):
        self.primary.toggle_fullscreen()

    def cycle_mode(self):
        self.primary.cycle_mode()

    def scale_true(self, f):
        self.primary.scale_true(f)

    def resize(self, size):
        self.primary.resize(size)

    def mode_name(self):
        return self.primary.mode_name()
