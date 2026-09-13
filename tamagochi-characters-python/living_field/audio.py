"""
Sound.

The Arduino cannot play Spotify, and it is worth being clear about why rather
than treating it as a limitation to work around: Spotify streams are
DRM-protected, need OAuth and TLS and an audio codec, and the API does not hand
raw audio to third-party devices at all. The board has thirty-two kilobytes of
memory and no music-capable output. There is nothing to port.

So the board is the CONTROLLER and the laptop is the PLAYER:

    knobs -> Arduino -> USB serial -> laptop -> Spotify, already running

On a Mac this needs no tokens and no Web API, because Spotify.app is
scriptable. `tell application "Spotify" to set sound volume to 60` is the whole
integration.

TWO KINDS OF SOUND, DELIBERATELY SEPARATE

  The music        Spotify. Background. If it fails, nothing is lost.
  The crowning     a local file, played with afplay.

The second one does not go through Spotify on purpose. The moment a crew crosses
the line is the one sound in the piece that has to be instant and certain, and
routing it through a network call to a third-party app is how you get a fanfare
that arrives two seconds after the fireworks.

Everything here runs on a background thread and swallows its own failures. No
sound is worth a stutter on the building.
"""

import os
import subprocess
import threading

SOUNDS = os.path.join(os.path.dirname(__file__), "assets")


def _run(args):
    """Fire and forget. Never raises, never waits."""
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _osascript(script):
    def go():
        try:
            subprocess.run(["osascript", "-e", script], timeout=4,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    threading.Thread(target=go, daemon=True).start()


class Audio:
    """Spotify for the music, a local file for the moment that matters."""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self._last_volume = None

    # -- the music ---------------------------------------------------------
    def play(self, uri=None):
        """
        Start the music. `uri` is a Spotify URI like spotify:playlist:xxxx,
        which you get from the app: right-click -> Share -> Copy Spotify URI.
        """
        if not self.enabled:
            return
        if uri:
            _osascript(f'tell application "Spotify" to play track "{uri}"')
        else:
            _osascript('tell application "Spotify" to play')

    def pause(self):
        if self.enabled:
            _osascript('tell application "Spotify" to pause')

    def volume(self, level):
        """
        0 to 1, straight off a knob.

        Only sent when it actually changes by a noticeable amount -- a
        potentiometer jitters by a percent or two constantly, and firing an
        AppleScript thirty times a second would spawn thirty processes a second
        for no reason.
        """
        if not self.enabled:
            return
        v = max(0, min(100, int(level * 100)))
        if self._last_volume is not None and abs(v - self._last_volume) < 3:
            return
        self._last_volume = v
        _osascript(f'tell application "Spotify" to set sound volume to {v}')

    def duck(self, level=25):
        """Pull the music down so something else can be heard over it."""
        if self.enabled:
            _osascript(f'tell application "Spotify" to set sound volume to {level}')

    # -- the moment that matters -------------------------------------------
    def cue(self, name):
        """Play a local sound now. Instant, local, no network anywhere."""
        path = os.path.join(SOUNDS, name)
        if os.path.exists(path):
            _run(["afplay", path])
            return True
        return False

    def crowning(self, duck_music=True):
        """The winner has crossed the line."""
        if duck_music:
            self.duck(20)
        return self.cue("crowning.wav")
