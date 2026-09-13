"""
Real weather, for a building that studies weather.

The Green Building houses the Department of Earth, Atmospheric and Planetary
Sciences, and it is famous for its wind -- I. M. Pei left the ground floor open
because of it, and Calder's Big Sail stands at its foot to break it. So the tree
on that facade sways with the wind that is actually blowing outside, and the
atmospheric layers sit at the temperature the air actually is.

This is the answer to "what physical thing can represent the building". Nothing
represents it better than its own measurements, and nobody can reasonably object
to a building showing what it is standing in.

HOW IT IS KEPT SAFE

A live installation must not depend on the internet, so this is built to be
ignorable:

  - It runs on a background thread and the drawing loop never waits for it.
  - It never raises. Any failure at all leaves the last known values in place.
  - The last reading is cached to disk, so a machine with no network on the
    night still opens with real weather from the last time it had one.
  - With no cache and no network it uses calm defaults and the piece looks
    exactly as it always does.

It only ever READS a public US National Weather Service feed. Nothing is sent,
nothing is stored about anybody, and no account or key is involved.
"""

import json
import os
import threading
import time
import urllib.request

# Logan, about five kilometres from the building, and the closest station with
# a continuous public feed. Wind on the Charles is near enough the same.
STATION = "KBOS"
URL = f"https://api.weather.gov/stations/{STATION}/observations/latest"

# The next sixteen hours over Cambridge, one entry an hour. This is what turns
# the facade from a light show into an instrument: the building can show what
# is COMING, not just what is happening, and a person across the river who
# learns to read it once always knows.
FORECAST_URL = "https://api.weather.gov/gridpoints/BOX/70,101/forecast/hourly"
CACHE = os.path.join(os.path.dirname(__file__), "..", "..", ".weather-cache.json")

REFRESH_SECONDS = 600.0        # ten minutes; the weather does not hurry
TIMEOUT = 8.0

# What to do when there is no reading at all.
DEFAULTS = {"wind_kmh": 12.0, "wind_dir": 250.0, "temp_c": 14.0,
            "description": "no reading"}

# One row of the building per hour ahead. Seventeen rows, so sixteen hours
# plus now.
HOURS = 17


class Weather:
    """The weather outside, or the best guess available."""

    def __init__(self, enabled=True):
        self.data = dict(DEFAULTS)
        self.source = "defaults"
        # rain chance and cloudiness for each hour ahead, 0 to 1
        self.hours = None
        self._stop = False
        self._load_cache()
        if enabled:
            threading.Thread(target=self._loop, daemon=True).start()

    # -- what the rest of the programme asks for ---------------------------
    @property
    def wind(self):
        """
        How hard it is blowing, as 0 to 1.

        Roughly: nothing at all is 0, a stiff 50 km/h is 1. Kept gentle at the
        bottom so a still night still has a little movement in it -- a tree
        that is perfectly rigid looks broken, not calm.
        """
        k = self.data.get("wind_kmh") or 0.0
        return max(0.12, min(1.0, k / 50.0))

    @property
    def wind_bias(self):
        """
        Which way it is leaning, as -1 (from the east) to +1 (from the west).

        The building's wide face looks roughly north over the Charles, so an
        east or west wind is the one you would actually see pushing a tree
        sideways. A northerly is blowing at the facade and barely leans it.
        """
        import math
        d = math.radians(self.data.get("wind_dir") or 0.0)
        return max(-1.0, min(1.0, math.sin(d)))

    @property
    def temp_c(self):
        return self.data.get("temp_c")

    def forecast_rows(self):
        """
        Sixteen hours ahead as (rain 0-1, cloud 0-1), roof first.

        The roof is the furthest ahead and the ground is now, so weather
        arrives by moving DOWN the building towards you -- which is the right
        way round, because that is how it feels.
        """
        if not self.hours:
            return None
        rows = list(self.hours)[:HOURS]
        while len(rows) < HOURS:
            rows.append(rows[-1])
        return [(r, c) for (r, c, _t) in reversed(rows)]

    def summary(self):
        d = self.data
        w = d.get("wind_kmh")
        t = d.get("temp_c")
        bits = []
        if w is not None:
            bits.append(f"wind {w:.0f} km/h")
        if t is not None:
            bits.append(f"{t:.0f}C")
        if d.get("description"):
            bits.append(str(d["description"]).lower())
        return f"{', '.join(bits)} ({self.source})" if bits else self.source

    def close(self):
        self._stop = True

    # -- the boring part ---------------------------------------------------
    def _loop(self):
        while not self._stop:
            self._fetch()
            self._fetch_forecast()
            for _ in range(int(REFRESH_SECONDS)):
                if self._stop:
                    return
                time.sleep(1.0)

    def _fetch(self):
        try:
            req = urllib.request.Request(
                URL, headers={"User-Agent": "living-field-hack140",
                              "Accept": "application/geo+json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                p = json.load(r)["properties"]

            def val(key):
                v = (p.get(key) or {}).get("value")
                return float(v) if v is not None else None

            got = {}
            if val("windSpeed") is not None:
                got["wind_kmh"] = val("windSpeed")
            if val("windDirection") is not None:
                got["wind_dir"] = val("windDirection")
            if val("temperature") is not None:
                got["temp_c"] = val("temperature")
            if p.get("textDescription"):
                got["description"] = p["textDescription"]

            if got:
                self.data.update(got)
                self.source = "live"
                self._save_cache()
        except Exception:
            # Silence is correct here. A weather feed being down is not a
            # reason for anything to change on a building.
            pass

    def _fetch_forecast(self):
        """The next sixteen hours, as numbers the facade can show."""
        try:
            req = urllib.request.Request(
                FORECAST_URL, headers={"User-Agent": "living-field-hack140",
                                       "Accept": "application/geo+json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                periods = json.load(r)["properties"]["periods"][:HOURS]
            rows = []
            for p in periods:
                pop = (p.get("probabilityOfPrecipitation") or {}).get("value")
                rain = (float(pop) / 100.0) if pop is not None else 0.0
                text = (p.get("shortForecast") or "").lower()
                # Cloudiness read off the words the forecast actually uses.
                if "clear" in text or "sunny" in text:
                    cloud = 0.05
                elif "mostly clear" in text or "mostly sunny" in text:
                    cloud = 0.25
                elif "partly" in text:
                    cloud = 0.5
                elif "mostly cloudy" in text:
                    cloud = 0.78
                elif "cloudy" in text or "overcast" in text:
                    cloud = 0.92
                else:
                    cloud = 0.5
                rows.append((rain, cloud, p.get("temperature")))
            if rows:
                self.hours = rows
        except Exception:
            pass

    def _load_cache(self):
        try:
            with open(os.path.abspath(CACHE)) as fh:
                cached = json.load(fh)
            if isinstance(cached, dict):
                self.data.update({k: v for k, v in cached.items() if k in DEFAULTS})
                self.source = "cached"
        except Exception:
            pass

    def _save_cache(self):
        try:
            with open(os.path.abspath(CACHE), "w") as fh:
                json.dump(self.data, fh)
        except Exception:
            pass
