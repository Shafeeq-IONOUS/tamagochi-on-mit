# Tower Tamagotchi

A crowd-raised pet for the MIT Green Building facade (17 floors x 9 windows, RGB, 30 fps).
Students from Boston/Cambridge schools feed and play with one shared mascot on the building.
Pure Python stdlib, no installs.

```bash
python3 mascot_show.py --instance <name>              # mascot lineup on the simulator (loops)
python3 mascot_show.py --instance <name> --only husky # one mascot
python3 mascot_show.py --clips clips/                 # .bin demo clips in the simulator's format
python3 main.py --instance <name>                     # the interactive pet + phone API
python3 main.py --bots 20 --hatched                   # fake crowd, local preview at :8140/preview
python3 -m unittest discover tests                    # flash-safety checks
```

Create a simulator instance at sundai.willsarg.com (event password required) and pass its name.

## Photosensitivity safety

Every output path runs through `tower/safety.py`'s `FlashGuard`:

- brightness fades instead of cutting (a full 0 → 255 swing takes at least 0.3 s)
- each window and the facade as a whole are tracked with the WCAG 2.3.1 flash definition
  (10% relative-luminance reversals); anything that would exceed **2 flashes/s** is held back
  (WCAG's limit is 3)

`tests/test_safety.py` proves the guard stops a 10 Hz strobe and checks every shipped animation.
Design rules on top of the guard: no strobes, no full-facade colour flashes, no blinking warnings,
slow hops (fast motion reads as flicker on a building this size), no pure 255 white (it blooms).

## Mascots

One 9 x 9 drawing each in `tamagotchi/mascots.py`; idle / blink / eat / sleep / sad poses are derived
from it (`E` = eye, `M` = mouth). The baby stage is the top rows of the drawing.

| Mascot | School |
| --- | --- |
| Tim the Beaver | MIT |
| John Harvard (pilgrim) | Harvard |
| Paws the Husky | Northeastern |
| Rhett the Terrier | BU |
| Jumbo the Elephant | Tufts |
| Baldwin the Eagle | Boston College |
| Make Way Duckling | every school without its own mascot |

The showcase routine (12 s each, on black): ride down the floors → idle + blink → eat → one hop →
doze off → wake → ride back up. In the interactive game the pet wears the mascot of whichever school
has interacted most in the last 5 minutes.

## Interactive game

| Floors | What's shown |
| --- | --- |
| 0 | Dim colour of the school that acted last |
| 1-11 | The mascot; food drops in, hearts float up |
| 12 | Ground; poop piles up when nobody cleans |
| 13-16 | Stat bars: hunger, happy, energy, clean (solid red under 20) |

The egg hatches after 50 crowd taps; baby → adult after 1500 care points; every 2 minutes a school
leaderboard takes over; 1-7am the pet sleeps and the facade dims.

### HTTP API (for the website)

| Method | Path | Body / response |
| --- | --- | --- |
| `POST` | `/api/action` | `{"action": "feed" \| "play" \| "pet" \| "clean" \| "sleep" \| "cheer", "school": "<id>"}` → `{"ok": true, "state": {...}}`; `429` if the same client acts within 0.6 s |
| `GET` | `/api/state` | `{stage, mood, stats{hunger,happy,energy,clean}, care, hatch_at, adult_at, hype, leaderboard[[school, n]], totals}` |
| `GET` | `/api/schools` | `[[id, display name], ...]` |
| `GET` | `/api/frame` | current 17 x 9 x `[r,g,b]` frame (draw a mini tower on the site) |

`tamagotchi/web/controller.html` is a bare reference client. The rate limit is keyed on client IP; if
the website proxies calls through its backend, forward a per-user id instead.

## Layout

```
mascot_show.py          mascot-only showcase: simulator, JSON export, .bin clips
main.py                 interactive game server + render loop
demo_reel.py            scripted 72 s story of the game
tamagotchi/mascots.py   mascot drawings + derived poses
tamagotchi/pet.py       stats, stages, actions, crowd metrics
tamagotchi/render.py    game state -> 17 x 9 frames
tamagotchi/sprites.py   egg + heart pixel art
tamagotchi/schools.py   school ids + tower colours
tower/display.py        Frame, WebDisplay (simulator), colour helpers
tower/safety.py         FlashGuard + WCAG flash analyzer
tower/font.py           3x5 pixel font + scroller
```
