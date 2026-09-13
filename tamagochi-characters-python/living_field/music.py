"""
Your DJ set, playing under the building.

Drop audio files in `music/` and they play. That is the whole thing.

WHY NOT SPOTIFY, AND WHY NOT afplay

Spotify is fine for a rehearsal and a bad idea on the night: it needs the
network, it puts ads between tracks on a free account, and playing copyrighted
music to a public square is a licensing question somebody at MIT would have to
answer. A folder of files has none of those problems.

afplay was the obvious tool and the wrong one -- it can only set a volume when
it starts, so the knob would do nothing until the next track. pygame's mixer is
already a dependency here, changes volume live, and can play the crowning
fanfare on its own channel OVER the music rather than instead of it. Which
matters, because the fanfare should land on top of the drop, not replace it.

  music/            put your set here (mp3, ogg, flac, wav)
  knob on A2        volume, live
  the crowning      plays over the top, and ducks the music while it rings

Nothing here can stall the drawing loop. Failures are silent: a demo with no
music is a demo; a demo that freezes is not.
"""

import os
import random
import threading

MUSIC_DIR = os.path.join(os.path.dirname(__file__), "..", "music")
PLAYABLE = (".mp3", ".ogg", ".flac", ".wav", ".m4a")

# How far the music drops while the fanfare rings, and how long it takes to
# come back. A hard cut sounds like a mistake; a duck sounds like a mix.
DUCK_TO = 0.22
DUCK_RECOVER = 2.6


class Music:
    """Plays a folder of files. Volume is live, so the knob works."""

    def __init__(self, folder=None, shuffle=False, enabled=True, fanfare=True):
        self.enabled = enabled
        # Whether the laptop rings the winner's fanfare itself. Turn it off
        # when the phones in the crowd are carrying that moment instead --
        # two victory sounds at once is a mess, not a celebration. Either
        # way the DJ set still ducks, so the room goes quiet for the win.
        self.fanfare_enabled = fanfare
        self.folder = os.path.abspath(folder or MUSIC_DIR)
        self.tracks = []
        self.index = 0
        self.ready = False
        self.playing = False
        self._want = 0.7          # what the knob asks for
        self._duck = 1.0          # 1.0 normally, less while ducked
        self._fanfare = None
        self._next_check = 0.0
        self._lock = threading.Lock()
        if not enabled:
            return
        try:
            import pygame
            if not pygame.mixer.get_init():
                # If nothing set a buffer already, ask for a generous one.
                # A small buffer is heard as stuttering under a busy render
                # loop, which is easy to mistake for a slow disk.
                try:
                    pygame.mixer.init(frequency=44100, size=-16,
                                      channels=2, buffer=4096)
                except Exception:
                    pygame.mixer.init()
            self._pg = pygame
            self.tracks = self._find()
            if shuffle:
                random.shuffle(self.tracks)
            cue = os.path.join(os.path.dirname(__file__), "assets", "crowning.wav")
            if os.path.exists(cue):
                self._fanfare = pygame.mixer.Sound(cue)
            self.ready = True
        except Exception:
            self.ready = False

    def _find(self):
        try:
            names = sorted(n for n in os.listdir(self.folder)
                           if n.lower().endswith(PLAYABLE) and not n.startswith("."))
        except Exception:
            return []
        return [os.path.join(self.folder, n) for n in names]

    # -- playing -----------------------------------------------------------
    def start(self):
        """Begin the set. Silently does nothing if there is nothing to play."""
        if not self.ready or not self.tracks:
            return False
        return self._load_and_play(0)

    def _load_and_play(self, i):
        try:
            self.index = i % len(self.tracks)
            self._pg.mixer.music.load(self.tracks[self.index])
            self._pg.mixer.music.set_volume(self._want * self._duck)
            self._pg.mixer.music.play()
            # Line up the next one so the gap between tracks is as small as
            # the decoder allows.
            if len(self.tracks) > 1:
                self._pg.mixer.music.queue(self.tracks[(self.index + 1) % len(self.tracks)])
            self.playing = True
            return True
        except Exception:
            self.playing = False
            return False

    def tick(self, dt):
        """
        Keep the set going and let a duck recover. Called every frame; does
        almost nothing almost always.
        """
        if not self.ready:
            return
        if self._duck < 1.0:
            self._duck = min(1.0, self._duck + dt / DUCK_RECOVER)
            self._apply()
        # Only ask the mixer whether it is still going twice a second. Asking
        # it thirty times a second is thirty needless trips into SDL per frame,
        # in the same loop that must not be late for the audio callback.
        if self.playing:
            self._next_check -= dt
            if self._next_check <= 0.0:
                self._next_check = 0.5
                try:
                    if not self._pg.mixer.music.get_busy():
                        self._load_and_play(self.index + 1)
                except Exception:
                    pass

    def volume(self, level):
        """0 to 1, straight off the knob."""
        level = max(0.0, min(1.0, float(level)))
        if abs(level - self._want) < 0.01:
            return
        self._want = level
        self._apply()

    def _apply(self):
        if not self.ready:
            return
        try:
            self._pg.mixer.music.set_volume(self._want * self._duck)
        except Exception:
            pass

    # -- the moment that matters -------------------------------------------
    def crowning(self):
        """
        The fanfare, over the top of whatever is playing.

        On its own channel on purpose, so it lands on the music rather than
        replacing it, and so it is instant -- no file to open, no network, no
        third-party app to ask.
        """
        if not self.ready:
            return False
        self._duck = DUCK_TO
        self._apply()
        if self._fanfare is not None and self.fanfare_enabled:
            try:
                self._fanfare.play()
                return True
            except Exception:
                pass
        return False

    def stop(self):
        if self.ready:
            try:
                self._pg.mixer.music.fadeout(600)
            except Exception:
                pass
        self.playing = False

    def status(self):
        if not self.ready:
            return "no audio"
        if not self.tracks:
            return f"no music in {os.path.basename(self.folder)}/"
        name = os.path.basename(self.tracks[self.index])
        if len(name) > 26:
            name = name[:24] + ".."
        return f"{'>' if self.playing else '||'} {name}  {int(self._want*100)}%"
