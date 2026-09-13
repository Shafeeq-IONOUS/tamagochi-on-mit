"""
The twenty minutes.

Everything else in this project is built so the building behaves on its own.
That is right for an installation and wrong for a demo: on a stage you have one
slot, the room is watching, and you cannot stand there hoping the creature gets
curious on cue.

So this is a director. It walks the building through the story in order, on a
clock, while leaving every real system running underneath -- the brain still
reasons, the tree still grows, the weather is still real. Nothing is faked. The
director only decides WHEN, the same way a stage manager does not act.

Press D to start it, D again to stop and hand control back.

THE STORY IT TELLS

A Tamagotchi, essentially, which is what the thing already is: a creature that
stays alive because people show up.

  1  ALONE      it is doing its job. Showing the weather to a city that is
                not looking. This is most of its life.
  2  SPEAKS     it says what is coming, in words, because a stranger cannot
                read a gradient they were never taught.
  3  NOTICED    somebody is there. The light comes down the tower.
  4  STARTLED   touched again while already alert -- it flinches, and then
                it watches.
  5  THE CROWD  everybody presses at once. A tree grows out of the room.
  6  REMEMBERS  the crowd has gone. What they grew is still there.
  7  DREAMS     tired and alone, it replays the evening.
  8  ALONE      back to work. The weather has not stopped.

The last beat is the point of the whole thing: it returns to being useful. The
crowd was the event; the instrument is the job.
"""

import time

# (seconds from the start, world to express, one line for the presenter)
SCRIPT = [
    (0,    "forecast",  "It is doing its job. Sixteen hours of weather, one hour per floor."),
    (25,   "forecast",  "Now it says it out loud -- for anyone who was never taught to read it."),
    (55,   "attention", "Somebody is there. Watch the light come down the building."),
    (85,   "startle",   "Touched again, already alert. It flinches -- then it watches you."),
    (115,  "tree",      "Everybody press. This is your tree."),
    (245,  "memory",    "They have gone. What they grew is still on the building."),
    (280,  "dream",     "Tired, and alone. It is replaying the evening."),
    (320,  "forecast",  "And back to work. The weather did not stop for any of this."),
]

SAY_WEATHER_AT = 25      # trigger the words at this beat
CROWD_OPENS_AT = 115     # when the room should be pressing


class Director:
    """Runs the story on a clock. Never touches the renderer, only the choice."""

    def __init__(self):
        self.running = False
        self._began = 0.0
        self._beat = -1
        self.line = ""

    def start(self, t):
        self.running = True
        self._began = t
        self._beat = -1
        self.line = ""

    def stop(self):
        self.running = False
        self.line = ""

    def toggle(self, t):
        self.stop() if self.running else self.start(t)

    @property
    def elapsed(self):
        return self._elapsed

    def update(self, t):
        """
        Returns (world_name or None, just_started_a_beat).

        None means "no opinion" -- which is what it returns when it is not
        running, so the building goes straight back to deciding for itself.
        """
        if not self.running:
            self._elapsed = 0.0
            return None, False

        self._elapsed = t - self._began
        beat = -1
        for i, (at, _w, _line) in enumerate(SCRIPT):
            if self._elapsed >= at:
                beat = i
        if beat < 0:
            return None, False

        fresh = beat != self._beat
        self._beat = beat
        self.line = SCRIPT[beat][2]
        return SCRIPT[beat][1], fresh

    def status(self):
        if not self.running:
            return ""
        m, s = divmod(int(self._elapsed), 60)
        return f"DEMO {m}:{s:02d} - {self.line}"

    _elapsed = 0.0
