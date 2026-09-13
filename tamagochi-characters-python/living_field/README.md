# Living Field

A Python renderer for the Green Building facade, written against the same
`gbsim` display interface already in this repo. It runs in a window, on the
simulator, or on the building — one line apart.

```
cd tamagochi-characters-python
python3 run_living_field.py                 # a window
python3 run_living_field.py plucky-eagle    # window + the simulator
```

Needs `numpy` and `pygame-ce`. Optionally `pyserial` (Arduino) and `hyperon`
(MeTTa — see the note on Python versions below).

## What it is

Eleven ways for the building to behave, a small mind that chooses between them,
and a race.

| key | | |
|---|---|---|
| `1`–`5` | Sounding, Aurora, Seismic, Radar, Reef | weather — what the people inside the building study |
| `6`–`9` | Attention, Startle, Memory, Dream | these exist only because somebody is there |
| `t` | Tree | the crowd grows one tree together, all evening |
| — | Forecast | **the next 16 hours, one hour per floor** — the default when nobody is around |
| `r` | **King of the Charles** | four crews, the room rows them, the winner gets fireworks |
| `d` | the demo | walks the whole story on a clock |
| `m` | say the weather in words | |
| `0` | hand control back to the building | |

## How it decides

Three speeds, deliberately kept apart:

- **30 a second** — drawing. Arithmetic only, never waits for anything.
- **twice a second** — thinking. `brain.metta` says which behaviours are
  *appropriate*; `learner.py` picks the one that has actually been holding
  people, learned through the sensor. Symbolic reasoning decides what is
  allowed, learning decides what is good — so it can never learn its way into
  flinching at everybody, because the rules do not offer that unless it has
  genuinely been startled.
- **once an evening** — remembering. Every touch is kept.

## Two things worth stealing regardless of the rest

**`governor.py`** — every frame passes through it and nothing can skip it.
Brightness capped at 85% (applied last, so nothing downstream can undo it), the
whole facade limited to 36%/sec, and **no single window may change faster than
66%/sec**. That last rule exists because the facade-average limit is not enough:
one window can flash while its neighbour dims and the average never moves.
Measured before it existed — individual windows swinging 454% of full brightness
per second inside frames that looked calm.

**`trueview.py`** — shows the flattering view and a blurred thumbnail of what a
person on Memorial Drive actually sees, side by side. It found real problems:
the resting building measured 0% contrast (every window identical), and text
turned out to be *legible* at this size when I had assumed it was impossible.

## Notes for this repo

- Imports come from `gbsim.display`, and sending to the simulator uses
  `gbsim.web.WebDisplay` — this started with its own copy and gbsim's is better
  (keep-alive connection, latest-wins mailbox). `mirror.py` just draws to the
  local window and the simulator at once.
- Independently hit the same Cloudflare wall gbsim documents: the default
  `Python-urllib` user agent gets a 403.
- The simulator's tree line hides the bottom two rows, so the forecast keeps
  "now" above it. Anything meaningful has to live above row 14.
- **MeTTa is optional.** `hyperon` only ships wheels for Python 3.10–3.12. On
  anything newer the same rules are read by a small matcher in `brain.py` —
  one rules file, two engines, verified to agree on all 324 possible inputs.
  The status bar says which one is running.

## Overlap with the race already here

`race.py` is a four-crew race up the building and it was written before I found
`race-worker/` and the cheer page. **It should probably be thrown away** in
favour of the worker, which already has the mascots, the state and a front end —
this one has no sprites and only knows about lanes and positions.

What might be worth keeping from it: the finale (`finale()` in `race.py`), which
is eleven seconds of fireworks built to stay inside the safety limits. Crackle
is impossible — no window may go dark-to-full in under 1.5 seconds — but at 400
metres the crackle is already gone, and the swell, the fall and the afterglow
are not. Measured: 34x swell, zero frames over any limit.
