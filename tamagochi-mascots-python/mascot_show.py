"""Mascot showcase: each school's mascot takes the tower, on black, for 12 seconds.

No backgrounds, no text, no flashing - just the character moving through its poses:
ride down the floors -> idle + blink -> eat -> hop -> doze off -> wake -> ride up and away.
Every frame goes through FlashGuard, so brightness never changes faster than tower.safety allows.

    python3 mascot_show.py --instance <name>              # loop the lineup on the simulator
    python3 mascot_show.py --instance <name> --only husky # one mascot
    python3 mascot_show.py --out show.json                # export frames (base64 RGB, 30 fps)
    python3 mascot_show.py --clips clips/                 # simulator demo clips, one .bin per mascot
"""

import argparse
import base64
import json
import math
import os
import struct
import time

from tamagotchi import mascots, schools
from tower.display import COLS, MAX_FPS, ROWS, Frame, WebDisplay
from tower.safety import FlashGuard

FPS = MAX_FPS
SEGMENT = 12.0
REST_TOP = (ROWS - 9) // 2  # sprite top row when centred on the tower

# (start, end, action) - one mascot's 12-second routine
ROUTINE = [
    (0.0, 2.0, "enter"),
    (2.0, 4.0, "idle"),
    (4.0, 5.6, "eat"),
    (5.6, 7.6, "hop"),
    (7.6, 9.6, "sleep"),
    (9.6, 10.6, "idle"),
    (10.6, 12.0, "leave"),
]


def ease(x):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, x)))


def pose_at(t):
    """(pose name, sprite top row) for a moment in the routine."""
    start, end, action = next(step for step in ROUTINE if step[0] <= t < step[1])
    k = (t - start) / (end - start)
    local = t - start
    if action == "enter":   # rides down the floors like an elevator
        return "idle", round(-9 + (REST_TOP + 9) * ease(k))
    if action == "leave":   # and back up and off the roof
        return "idle", round(REST_TOP - (REST_TOP + 9) * ease(k))
    if action == "eat":     # chomps a little over once a second
        return ("eat" if (local % 0.75) < 0.375 else "idle"), REST_TOP
    if action == "hop":     # one slow hop of three floors (fast hops read as flicker)
        return "idle", REST_TOP - round(3 * math.sin(math.pi * k))
    if action == "sleep":   # eyes shut, settles one floor lower
        return "sleep", REST_TOP + (1 if k > 0.15 else 0)
    blink = (local % 2.0) > 1.85
    bob = 1 if (local % 2.0) < 1.0 else 0   # slow breathing bob
    return ("blink" if blink else "idle"), REST_TOP - bob


def segment(mascot):
    sheet = mascot.poses("adult")
    palette = mascot.colors()
    for i in range(int(SEGMENT * FPS)):
        pose, top = pose_at(i / FPS)
        f = Frame()
        f.blit(sheet[pose], top, (COLS - 9) // 2, palette)
        yield f


def lineup_frames(lineup):
    """All mascots back to back, through one FlashGuard so the hand-offs are soft too."""
    guard = FlashGuard()
    for m in lineup:
        for f in segment(m):
            yield guard.filter(f)


def rgb_bytes(frames):
    return bytes(v for f in frames for row in f.px for px in row for v in px)


def clip_bytes(frames):
    """The simulator's looping-clip format: b'C', fps, frame count (uint16 LE), then 459 bytes per frame."""
    return struct.pack("<cBH", b"C", FPS, len(frames)) + rgb_bytes(frames)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--instance")
    p.add_argument("--api", default="https://sundai.willsarg.com/api")
    p.add_argument("--only", choices=list(mascots.MASCOTS))
    p.add_argument("--out")
    p.add_argument("--clips", help="directory for simulator demo clips (<mascot>.bin + lineup.bin)")
    p.add_argument("--once", action="store_true", help="play one pass instead of looping")
    args = p.parse_args()
    lineup = [mascots.MASCOTS[args.only]] if args.only else list(mascots.MASCOTS.values())

    if args.clips:
        os.makedirs(args.clips, exist_ok=True)
        for m in lineup:
            with open(os.path.join(args.clips, f"{m.id}.bin"), "wb") as fh:
                fh.write(clip_bytes(list(lineup_frames([m]))))
        with open(os.path.join(args.clips, "lineup.bin"), "wb") as fh:
            fh.write(clip_bytes(list(lineup_frames(lineup))))
        print(f"wrote {len(lineup) + 1} clips to {args.clips}")
    if args.out:
        out = [{"id": m.id, "name": m.name, "school": schools.name(m.school),
                "frames": base64.b64encode(rgb_bytes(lineup_frames([m]))).decode()} for m in lineup]
        with open(args.out, "w") as fh:
            json.dump({"fps": FPS, "rows": ROWS, "cols": COLS, "mascots": out}, fh)
        print(f"wrote {len(out)} mascots to {args.out}")
    if args.instance:
        display = WebDisplay(args.instance, args.api)
        print(f"playing on {display.url} (Ctrl+C to stop)")
        while True:
            for f in lineup_frames(lineup):
                started = time.monotonic()
                display.send(f)
                time.sleep(max(0.0, 1 / FPS - (time.monotonic() - started)))
            if args.once:
                break
    if not (args.out or args.clips or args.instance):
        p.print_help()


if __name__ == "__main__":
    main()
