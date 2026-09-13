"""A scripted ~70 s story of the pet's life, for pitches and for testing on the simulator.

    python3 demo_reel.py --instance <name>     # play it on the simulator in real time
    python3 demo_reel.py --out reel.json       # export frames (hex strings, 30 fps)
"""

import argparse
import json
import random
import time

from tamagotchi.pet import ADULT_AT, Pet
from tamagotchi.render import Renderer
from tower.display import MAX_FPS, WebDisplay
from tower.safety import FlashGuard

FPS = MAX_FPS
DURATION = 72

# (start second, taps per second, action mix, school mix)
SCRIPT = [
    (0,  1.0, ["pet"], ["mit"]),                                    # a lonely egg, first taps
    (6,  6.0, ["cheer", "pet"], ["mit", "harvard", "bu"]),          # crowd shows up -> hatch
    (14, 1.2, ["feed", "pet", "play", "clean"], ["mit", "harvard", "tufts"]),
    (28, 0.0, [], []),                                              # everyone goes to class
    (38, 5.0, ["feed", "play", "clean", "sleep", "pet"], ["harvard", "mit", "neu", "berklee", "bu"]),
    (58, 2.5, ["cheer"], ["mit", "harvard", "wellesley", "olin"]),  # grown up, fireworks
]
NEGLECT_AT = 30          # stats crash to show the sad / blinking-bar states
ADULT_FROM = 58
LEADERBOARD_EVERY = 50   # so the leaderboard takeover lands at 50-58 s


def frames():
    rng = random.Random(140)
    base = time.mktime(time.strptime("2026-09-17 12:00:00", "%Y-%m-%d %H:%M:%S"))  # noon: no night dimming
    pet = Pet()
    pet.last_tick = base
    renderer = Renderer(pet, start=base, leaderboard_every=LEADERBOARD_EVERY)
    guard = FlashGuard()
    next_tap = 0.0
    for i in range(DURATION * FPS):
        t = i / FPS
        now = base + t
        _, rate, actions, crowd = [s for s in SCRIPT if s[0] <= t][-1]
        if rate and t >= next_tap:
            pet.act(rng.choice(actions), rng.choice(crowd), now)
            next_tap = t + rng.expovariate(rate)
        if abs(t - NEGLECT_AT) < 1 / FPS / 2:
            pet.stats.update(hunger=12, happy=18, energy=40, clean=10)
        if abs(t - ADULT_FROM) < 1 / FPS / 2:
            pet.care = ADULT_AT
            pet.stats.update(hunger=90, happy=95, energy=85, clean=90)
        pet.tick(now)
        yield guard.filter(renderer.render(now))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--instance")
    p.add_argument("--api", default="https://sundai.willsarg.com/api")
    p.add_argument("--out")
    args = p.parse_args()

    if args.out:
        hexframes = ["".join("%02x%02x%02x" % px for row in f.px for px in row) for f in frames()]
        with open(args.out, "w") as fh:
            json.dump({"fps": FPS, "rows": 17, "cols": 9, "frames": hexframes}, fh)
        print(f"wrote {len(hexframes)} frames to {args.out}")
    if args.instance:
        display = WebDisplay(args.instance, args.api)
        for f in frames():
            started = time.monotonic()
            display.send(f)
            time.sleep(max(0.0, 1 / FPS - (time.monotonic() - started)))
    if not (args.out or args.instance):
        p.print_help()


if __name__ == "__main__":
    main()
