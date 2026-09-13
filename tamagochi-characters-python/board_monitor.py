#!/usr/bin/env python3
"""
Talk to the Arduino from Python. No IDE.

    python3 board_monitor.py            watch every input, live
    python3 board_monitor.py --list     which ports look like a board
    python3 board_monitor.py --raw      the raw lines, like a serial monitor
    python3 board_monitor.py --matrix   send a test pattern to the board's LED grid

WHY THIS EXISTS

A serial port can only be held by ONE program at a time. The Arduino IDE's
Serial Monitor holds it the whole time that window is open, which means the
building app cannot read the board and fails silently -- it just decides there
is no Arduino and carries on breathing.

So: close the IDE's Serial Monitor, and use this instead. It shows the same
thing, plus it interprets the numbers rather than making you read raw commas.

Same rule applies here: quit this before starting the building app, or the app
will not see the board either.
"""

import argparse
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial is missing.  ~/hack140/.venv-311/bin/python3 -m pip install pyserial")

BAUD = 115200


def find_ports():
    return [p for p in list_ports.comports()
            if any(k in (p.device or "") for k in ("usbmodem", "usbserial", "wchusb"))]


def open_board(port=None):
    ports = find_ports()
    if port:
        chosen = port
    elif not ports:
        sys.exit("No board found. Is it plugged in? Try:  python3 board.py --list")
    else:
        chosen = ports[0].device
    try:
        s = serial.Serial(chosen, BAUD, timeout=1)
    except serial.SerialException as e:
        if "Resource busy" in str(e) or "Errno 16" in str(e):
            sys.exit(f"{chosen} is busy -- something else has it open.\n"
                     "Almost always the Arduino IDE's Serial Monitor. Close that window\n"
                     "(the magnifying glass, top right) and try again.")
        sys.exit(f"Could not open {chosen}: {e}")
    return s, chosen


def bar(v, width=22):
    n = int(max(0.0, min(1.0, v)) * width)
    return "#" * n + "." * (width - n)


def watch(port=None):
    s, name = open_board(port)
    print(f"listening to {name}\n")
    time.sleep(2.0)                 # opening the port resets the board
    s.reset_input_buffer()
    print(f"{'light':>6} {'':22}  {'knock':>5}  {'volume':>6} {'':16}  {'bright':>6}")
    quiet_since = time.time()
    knocks = 0
    while True:
        try:
            line = s.readline().decode("ascii", "ignore").strip()
        except KeyboardInterrupt:
            break
        except Exception:
            continue
        if not line:
            if time.time() - quiet_since > 4:
                print("\n  ...silence. Is a sketch flashed? Is the baud 115200?")
                quiet_since = time.time()
            continue
        quiet_since = time.time()
        parts = line.split(",")
        try:
            light = int(parts[0])
            knock = parts[1].strip() == "1"
            vol = int(parts[2]) if len(parts) > 2 else None
            brt = int(parts[3]) if len(parts) > 3 else None
        except (ValueError, IndexError):
            print("  ?", line)
            continue
        if knock:
            knocks += 1
        v = f"{vol:5d} {bar(vol / 1023, 16)}" if vol is not None else "   -- (no knob wired)"
        b = f"{brt:5d}" if brt is not None else "  --"
        print(f"\r{light:6d} {bar(1 - light / 1023)}  "
              f"{'KNOCK' if knock else '     '}  {v}  {b}   taps:{knocks}",
              end="", flush=True)
    s.close()


def raw(port=None):
    s, name = open_board(port)
    print(f"raw from {name} -- ctrl-C to stop\n")
    time.sleep(2.0)
    s.reset_input_buffer()
    try:
        while True:
            line = s.readline().decode("ascii", "ignore").rstrip()
            if line:
                print(" ", line)
    except KeyboardInterrupt:
        pass
    s.close()


def matrix(port=None):
    """
    Send a test pattern to the board's own 12x8 LED grid.

    Proves the laptop-to-board direction works, which is the half people forget
    to check until the demo.
    """
    s, name = open_board(port)
    print(f"sending patterns to {name} -- ctrl-C to stop\n")
    time.sleep(2.0)
    frames = {
        "all on":      "1" * 96,
        "checker":     "".join("1" if (i // 12 + i) % 2 == 0 else "0" for i in range(96)),
        "left half":   "".join("1" if (i % 12) < 6 else "0" for i in range(96)),
        "top rows":    "".join("1" if (i // 12) < 4 else "0" for i in range(96)),
        "all off":     "0" * 96,
    }
    try:
        while True:
            for label, bits in frames.items():
                print(f"  {label}")
                s.write(("M:" + bits + "\n").encode())
                time.sleep(1.2)
    except KeyboardInterrupt:
        s.write(("M:" + "0" * 96 + "\n").encode())
    s.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Talk to the Arduino without the IDE.")
    ap.add_argument("--list", action="store_true", help="show ports that look like a board")
    ap.add_argument("--raw", action="store_true", help="print raw lines")
    ap.add_argument("--matrix", action="store_true", help="test the board's LED grid")
    ap.add_argument("--port", help="use this port instead of guessing")
    a = ap.parse_args()

    if a.list:
        found = find_ports()
        if not found:
            print("No board-looking ports. All ports:")
            for p in list_ports.comports():
                print("  ", p.device, "-", p.description)
        else:
            for p in found:
                print("  ", p.device, "-", p.description)
    elif a.raw:
        raw(a.port)
    elif a.matrix:
        matrix(a.port)
    else:
        watch(a.port)
