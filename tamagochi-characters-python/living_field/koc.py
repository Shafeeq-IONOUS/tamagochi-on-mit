"""
King of the Charles -- the team's race, watched from here.

The race itself lives in binam's Cloudflare worker. The admin panel starts and
stops it, the cheer page collects taps, and the whole thing is authoritative
there. This just watches, so that the music and the building follow whatever
the admin does rather than needing their own set of buttons.

WHY THE MUSIC LIVES HERE AND NOT IN THE BROWSER

The obvious version is to play the track on every phone. It sounds terrible.
Forty handsets a few hundred milliseconds apart in one room is a smeared echo,
not a soundtrack -- which is why silent discos synchronise over radio rather
than trusting the web. On top of that browsers refuse to start audio without a
tap, and a 348 MB set is not going out to forty devices over venue wifi.

So: one sound source, on the machine that is plugged into the PA, following the
race. Pressing Start in the admin panel starts the music, because this notices.

Polls twice a second on a background thread. Never blocks, never raises. If the
worker is unreachable the last known state stands, and if there never was one
the race is simply "idle" and everything carries on.
"""

import json
import threading
import time
import urllib.request

API = "https://green-building-race.binamkayastha.workers.dev"
POLL_SECONDS = 0.5
TIMEOUT = 3.0

# The statuses the worker reports. Anything not in here is treated as idle,
# so a new phase added on their side cannot break this.
RUNNING = {"intro", "countdown", "racing", "running", "cheering"}
OVER = {"finished", "champion", "done"}

SCHOOLS = ("harvard", "mit", "neu", "bu")   # same order as our lanes


class KingOfCharles:
    """A read-only view of the team's race."""

    def __init__(self, api=API, enabled=True):
        self.api = api.rstrip("/")
        self.status = "idle"
        self.cheers = {s: 0 for s in SCHOOLS}
        self.progress = {s: 0.0 for s in SCHOOLS}
        self.winner = None
        self.introducing = None
        self.reachable = False
        self.last_seen = 0.0
        self._stop = False
        self._prev_status = "idle"
        self._events = []
        self._lock = threading.Lock()
        if enabled:
            threading.Thread(target=self._loop, daemon=True).start()

    # -- what the rest of the programme asks -------------------------------
    @property
    def running(self):
        return self.status in RUNNING

    @property
    def finished(self):
        return self.status in OVER

    def take_events(self):
        """
        What has just happened, since last asked: "started", "finished",
        "stopped". Read once, so an event is acted on exactly once.
        """
        with self._lock:
            e, self._events = self._events, []
        return e

    def summary(self):
        if not self.reachable:
            return "race: offline"
        if self.winner:
            return f"race: {self.winner} wins"
        if self.introducing:
            return f"race: introducing {self.introducing}"
        lead = max(self.progress, key=self.progress.get) if self.progress else "-"
        return f"race: {self.status} ({lead} ahead)"

    def close(self):
        self._stop = True

    # -- the boring part ---------------------------------------------------
    def _loop(self):
        while not self._stop:
            self._poll()
            time.sleep(POLL_SECONDS)

    def _poll(self):
        try:
            req = urllib.request.Request(
                f"{self.api}/api/state",
                headers={"User-Agent": "living-field/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                d = json.load(r)
        except Exception:
            # A worker being briefly unreachable is not a reason for anything
            # on the building to change.
            if time.time() - self.last_seen > 15:
                self.reachable = False
            return

        self.reachable = True
        self.last_seen = time.time()
        self.status = str(d.get("status") or "idle")
        self.winner = d.get("winner") or d.get("champion")
        self.introducing = d.get("introducing")

        cheers = d.get("cheers") or {}
        cols = d.get("progressCols") or {}
        for s in SCHOOLS:
            self.cheers[s] = int(cheers.get(s) or 0)
            # progressCols counts finish columns, 8 of them. Normalise so the
            # rest of this project can keep thinking in 0 to 1.
            self.progress[s] = min(1.0, float(cols.get(s) or 0) / 8.0)

        was, now = self._prev_status, self.status
        if was != now:
            self._prev_status = now
            with self._lock:
                if now in RUNNING and was not in RUNNING:
                    self._events.append("started")
                elif now in OVER and was not in OVER:
                    self._events.append("finished")
                elif now not in RUNNING and now not in OVER and was in RUNNING:
                    self._events.append("stopped")
