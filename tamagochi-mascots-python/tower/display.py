"""Frame buffer + display sinks for the 17 x 9 Green Building facade.

A frame is 17 rows (floors, top = row 0) x 9 columns (windows) of (r, g, b).
Sinks never get more than 30 frames per second.
"""

import json
import os
import ssl
import threading
import time
import urllib.request

MACOS_CA_BUNDLE = "/etc/ssl/cert.pem"
ROWS = 17
COLS = 9
MAX_FPS = 30

Color = tuple  # (r, g, b), 0-255

# Full 255 white blooms into a blob on the lit facade; this is the brightest "white" worth using.
WHITE = (205, 205, 205)


def clamp(v):
    return max(0, min(255, int(v)))


def scale(c, k):
    return (clamp(c[0] * k), clamp(c[1] * k), clamp(c[2] * k))


def mix(a, b, t):
    return tuple(clamp(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hsv(h, s=1.0, v=1.0):
    h = (h % 1.0) * 6
    i = int(h)
    f = h - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]
    return (clamp(r * 255), clamp(g * 255), clamp(b * 255))


class Frame:
    def __init__(self, fill=(0, 0, 0)):
        self.px = [[fill] * COLS for _ in range(ROWS)]

    def set(self, row, col, color):
        if 0 <= row < ROWS and 0 <= col < COLS and color is not None:
            self.px[row][col] = color

    def get(self, row, col):
        return self.px[row][col]

    def add(self, row, col, color, alpha=1.0):
        """Additive blend, handy for glows and particles."""
        if 0 <= row < ROWS and 0 <= col < COLS:
            base = self.px[row][col]
            self.px[row][col] = tuple(clamp(base[i] + color[i] * alpha) for i in range(3))

    def fill_row(self, row, color):
        for c in range(COLS):
            self.set(row, c, color)

    def blit(self, sprite, top, left, palette):
        """Draw a sprite (list of strings) using palette chars; '.' is transparent."""
        for r, line in enumerate(sprite):
            for c, ch in enumerate(line):
                if ch != "." and ch in palette:
                    self.set(top + r, left + c, palette[ch])

    def to_json(self):
        return json.dumps([[list(p) for p in row] for row in self.px])


def _ssl_context():
    """Default TLS verification; python.org builds on macOS ship without CA certs, so fall back
    to the system bundle rather than failing every request."""
    ctx = ssl.create_default_context()
    if not ctx.cert_store_stats()["x509_ca"] and os.path.exists(MACOS_CA_BUNDLE):
        ctx.load_verify_locations(MACOS_CA_BUNDLE)
    return ctx


class WebDisplay:
    """Pushes frames to the simulator (or the real building) over HTTP.

    POST {base}/i/{instance}/frame with a 17 x 9 x [r,g,b] JSON body.
    Sending happens on a background thread so a slow network never stalls the game loop;
    only the newest frame is kept.
    """

    def __init__(self, instance, base="https://sundai.willsarg.com/api", token=None):
        self.url = f"{base.rstrip('/')}/i/{instance}/frame"
        self.token = token or os.environ.get("TOWER_TOKEN")
        self._ssl = _ssl_context()
        self._latest = None
        self._cv = threading.Condition()
        self.errors = 0
        threading.Thread(target=self._pump, daemon=True).start()

    def send(self, frame):
        with self._cv:
            self._latest = frame.to_json()
            self._cv.notify()

    def _pump(self):
        interval = 1.0 / MAX_FPS
        while True:
            with self._cv:
                while self._latest is None:
                    self._cv.wait()
                body, self._latest = self._latest, None
            started = time.monotonic()
            # Cloudflare in front of the sim rejects urllib's default User-Agent (error 1010).
            headers = {"Content-Type": "application/json", "User-Agent": "tower-tamagotchi/1"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            req = urllib.request.Request(self.url, data=body.encode(), headers=headers, method="POST")
            try:
                urllib.request.urlopen(req, timeout=2, context=self._ssl).read()
            except OSError as e:  # network hiccup: drop this frame, keep the show running
                self.errors += 1
                if self.errors in (1, 10, 100) or self.errors % 1000 == 0:
                    print(f"[WebDisplay] send failed ({self.errors}x): {e}")
            time.sleep(max(0.0, interval - (time.monotonic() - started)))


class MemoryDisplay:
    """Keeps the last frame around so the local preview page can show it."""

    def __init__(self):
        self.last = Frame()

    def send(self, frame):
        self.last = frame


class MultiDisplay:
    def __init__(self, *sinks):
        self.sinks = [s for s in sinks if s]

    def send(self, frame):
        for s in self.sinks:
            s.send(frame)
