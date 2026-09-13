"""
The building's sense of touch.

Reads the two numbers the Arduino is shouting down the USB cable and turns them
into something the field can use. If there is no Arduino, no cable, or no
serial library installed, this quietly reports "nobody there" forever and the
building carries on breathing.

That last part is the whole design. On the night, a kicked cable must look like
nobody is standing there -- not like a crash.
"""

import threading
import time


class NullSensor:
    """What you get when there is no hardware. Always calm, never fails."""
    available = False
    port = None

    def read(self):
        """Returns (hand_closeness 0..1, knocked_just_now)."""
        return 0.0, False

    def send_matrix(self, rgb, threshold=0.30):
        pass

    def close(self):
        pass


class SerialSensor:
    """
    Listens to the Arduino on a background thread.

    A background thread matters here. Reading a serial port can block, and a
    block inside the drawing loop is a visible stutter on a twenty-one storey
    building. The loop only ever reads the last value this thread wrote, which
    it can do instantly.
    """

    available = True

    # The sensor reading with nothing covering it gets learned automatically in
    # the first few seconds, so you do not have to re-calibrate for each room.
    CALIBRATION_SECONDS = 4.0

    def __init__(self, port, baud=115200):
        import serial  # imported here so the app still runs without pyserial
        self.port = port
        self._ser = serial.Serial(port, baud, timeout=0.2)
        self._closeness = 0.0
        self._knock = False
        self._bright = None          # what "nobody there" looks like
        self._started = time.time()
        self._last_send = 0.0
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop:
            try:
                line = self._ser.readline().decode("ascii", "ignore").strip()
            except Exception:
                time.sleep(0.1)
                continue
            if not line or "," not in line:
                continue
            try:
                shadow_s, knock_s = line.split(",", 1)
                shadow = int(shadow_s)
                knock = knock_s.strip() == "1"
            except ValueError:
                continue

            # Learn the room. For the first few seconds, whatever the brightest
            # reading is counts as "nothing is covering the sensor".
            if self._bright is None or time.time() - self._started < self.CALIBRATION_SECONDS:
                self._bright = shadow if self._bright is None else max(self._bright, shadow)

            # How much of the light is being blocked, as 0 to 1.
            # A hand fully over the sensor is 1. An empty room is 0.
            span = max(self._bright * 0.55, 40.0)
            closeness = (self._bright - shadow) / span
            self._closeness = max(0.0, min(1.0, closeness))
            if knock:
                self._knock = True

    def read(self):
        knocked, self._knock = self._knock, False
        return self._closeness, knocked

    def send_matrix(self, rgb, threshold=0.30):
        """
        Send the tower back to the board, so its own little grid shows it too.

        The board has 12 x 8 LEDs and the building is 9 x 17, so the picture is
        turned on its side: the tower runs along the LONG axis of the matrix.
        Hold the board rotated a quarter turn and it reads as the building --
        which is the point, because the demo is holding the small one up beside
        the real one.

        Sent at most ten times a second, and never allowed to hold anything up:
        if the write would block or fail, it is simply skipped. A picture is a
        nice-to-have; the drawing loop is not.
        """
        now = time.time()
        if now - self._last_send < 0.1:
            return
        self._last_send = now

        lum = rgb[:, :, 0] * 0.30 + rgb[:, :, 1] * 0.59 + rgb[:, :, 2] * 0.11
        peak = float(lum.max())
        if peak <= 1e-6:
            return
        lum = lum / peak

        bits = []
        for mrow in range(8):                 # 8 rows  <- the building's width
            col = min(8, int(mrow * 9 / 8))
            for mcol in range(12):            # 12 cols <- the building's height
                row = min(16, int(mcol * 17 / 12))
                bits.append("1" if lum[row, col] > threshold else "0")

        try:
            self._ser.write(("M:" + "".join(bits) + "\n").encode("ascii"))
        except Exception:
            pass

    def close(self):
        self._stop = True
        try:
            self._ser.close()
        except Exception:
            pass


def open_sensor(preferred=None):
    """
    Find the Arduino and start listening, or return the do-nothing sensor.

    Never raises. Whatever goes wrong -- no library, no board, wrong cable,
    someone else using the port -- you get a NullSensor and the show goes on.
    """
    try:
        import serial
        from serial.tools import list_ports
    except ImportError:
        return NullSensor()

    candidates = []
    if preferred:
        candidates.append(preferred)
    for p in list_ports.comports():
        name = (p.device or "")
        # macOS names Arduino boards like /dev/cu.usbmodem1234
        if "usbmodem" in name or "usbserial" in name or "wchusb" in name:
            candidates.append(name)

    for port in candidates:
        try:
            return SerialSensor(port)
        except Exception:
            continue
    return NullSensor()
