"""
A pretend Arduino.

The board speaks a deliberately tiny protocol -- one line, thirty times a
second:

    812,0        <- plenty of light, no knock
    430,0        <- a hand is over the sensor
    790,1        <- somebody knocked

That is small enough to imitate exactly, so the whole chain from sensor to
lights can be tested with no hardware attached. Which matters, because the
hardware is the part most likely to be missing at the wrong moment, and
"we'll find out when we plug it in" is not a plan for the night of an install.

Run it on its own to watch the decoding:

    python3 -m living_field.fake_arduino
"""

import os
import pty
import time
import threading


class FakeArduino:
    """Opens a real serial port that nothing is plugged into."""

    def __init__(self, bright=810, quiet=True):
        self.bright = bright
        self._master, self._slave = pty.openpty()
        self.port = os.ttyname(self._slave)
        self._hand = 0.0          # 0 = nothing there, 1 = fully covered
        self._knock = False
        self._stop = False
        self._quiet = quiet
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop:
            # A hand blocks most of the light but never all of it, and there is
            # always a little noise on a real analogue pin.
            import random
            reading = int(self.bright * (1.0 - 0.72 * self._hand)
                          + random.uniform(-6, 6))
            knock = 1 if self._knock else 0
            self._knock = False
            try:
                os.write(self._master, f"{reading},{knock}\n".encode())
            except OSError:
                break
            time.sleep(1 / 30)

    # -- what a person standing there would do -----------------------------
    def hand(self, amount):
        """0 for nothing there, 1 for a hand right over the sensor."""
        self._hand = max(0.0, min(1.0, amount))

    def knock(self):
        self._knock = True

    def close(self):
        self._stop = True
        time.sleep(0.05)
        for fd in (self._master, self._slave):
            try:
                os.close(fd)
            except OSError:
                pass


def _demo():
    from living_field.sensor import SerialSensor
    fake = FakeArduino()
    print(f"fake board on {fake.port}\n")
    s = SerialSensor(fake.port)

    script = [(0.0, "nothing there", 0.0, False),
              (5.0, "hand approaching", 0.35, False),
              (6.5, "hand right over it", 0.95, False),
              (8.0, "hand away", 0.0, False),
              (9.0, "KNOCK", 0.0, True)]

    t0 = time.time()
    print(f"{'time':>6}  {'what happens':<20}{'closeness':>10}{'knock':>7}")
    for when, label, hand, knock in script:
        while time.time() - t0 < when:
            time.sleep(0.05)
        fake.hand(hand)
        if knock:
            fake.knock()
        time.sleep(0.45)
        c, k = s.read()
        print(f"{time.time()-t0:6.1f}  {label:<20}{c:10.2f}{str(k):>7}")

    s.close()
    fake.close()


if __name__ == "__main__":
    _demo()
