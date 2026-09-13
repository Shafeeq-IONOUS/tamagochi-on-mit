"""Tim the Tower Beaver - a crowd-raised Tamagotchi for the 17 x 9 Green Building display.

    python3 main.py --instance <name>            # drive the simulator instance
    python3 main.py --instance <name> --bots 20  # fake crowd, for demos and load tests

Serves a JSON API on :8140 for the website to call (see README).
"""

import argparse
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tamagotchi import schools
from tamagotchi.pet import ACTIONS, Pet
from tamagotchi.render import Renderer
from tower.display import MAX_FPS, MemoryDisplay, MultiDisplay, WebDisplay
from tower.safety import FlashGuard

COOLDOWN = 0.6  # seconds between actions from one phone, so nobody can solo the pet


def make_handler(pet, latest):
    last_action = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, status, body, content_type="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/state":
                self._send(200, pet.snapshot())
            elif path == "/api/frame":
                self._send(200, latest.last.to_json().encode())
            elif path == "/api/schools":
                self._send(200, [[k, v[0]] for k, v in schools.SCHOOLS.items()])
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/action":
                return self._send(404, {"error": "not found"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                action, school = body["action"], body.get("school", "other")
            except (ValueError, KeyError):
                return self._send(400, {"error": "expected {action, school}"})
            if action not in ACTIONS:
                return self._send(400, {"error": f"unknown action {action}"})
            if school not in schools.SCHOOLS:
                school = "other"
            client = self.client_address[0]
            now = time.time()
            if now - last_action.get(client, 0) < COOLDOWN:
                return self._send(429, {"error": "Easy there — Tim needs a sec 🦫"})
            last_action[client] = now
            pet.act(action, school)
            self._send(200, {"ok": True, "state": pet.snapshot()})

    return Handler


def run_bots(pet, n):
    """Simulated students, weighted so a couple of schools lead the leaderboard."""
    weights = {"mit": 6, "harvard": 5, "bu": 3, "neu": 3, "tufts": 2, "berklee": 2, "wellesley": 1, "olin": 1}
    ids, w = list(weights), list(weights.values())
    while True:
        time.sleep(random.expovariate(n / 8))  # each bot acts roughly every 8 s
        pet.act(random.choice(list(ACTIONS)), random.choices(ids, w)[0])


def render_loop(pet, display):
    renderer = Renderer(pet)
    interval = 1 / MAX_FPS
    while True:
        started = time.monotonic()
        pet.tick()
        display.send(renderer.render())
        time.sleep(max(0.0, interval - (time.monotonic() - started)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--instance", help="simulator instance name (from sundai.willsarg.com)")
    p.add_argument("--api", default="https://sundai.willsarg.com/api")
    p.add_argument("--port", type=int, default=8140)
    p.add_argument("--bots", type=int, default=0, help="number of simulated students")
    p.add_argument("--hatched", action="store_true", help="skip the egg stage")
    args = p.parse_args()

    pet = Pet()
    if args.hatched:
        pet.care, pet.born = 60, time.time() - 10
    latest = MemoryDisplay()
    web = WebDisplay(args.instance, args.api) if args.instance else None
    threading.Thread(target=render_loop, args=(pet, FlashGuard(MultiDisplay(latest, web))), daemon=True).start()
    if args.bots:
        threading.Thread(target=run_bots, args=(pet, args.bots), daemon=True).start()

    print(f"API: http://localhost:{args.port}/api/state")
    if web:
        print(f"pushing frames to {web.url}")
    ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(pet, latest)).serve_forever()


if __name__ == "__main__":
    main()
