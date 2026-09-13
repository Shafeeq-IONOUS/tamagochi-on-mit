"""
Run the living field.

    ~/hack140/start

------------------------------------------------------------------------------
Controls
------------------------------------------------------------------------------
    1 .. 9    force a world, and hold it there
              1 Sounding  2 Aurora  3 Seismic  4 Radar  5 Reef
              6 Attention 7 Startle 8 Memory   9 Dream
    T         the tree the crowd grows
    0         hand control back to the building -- it decides for itself again
    SPACE     touch it, at the foot of the tower
    click     touch it anywhere on the grid
    D         run the twenty-minute demo story (D again to stop)
    P         start / stop the music in music/
    R         start King of the Charles -- four crews, the room rows them
    S         fire the rare surge now (it also happens on its own)
    M         say the weather in words now (it also does this on its own,
              for about sixteen seconds every two and a half minutes)
    A         ambient activity on and off
    V         layout: design -> present -> pure
    + / -     resize the across-the-river view
    F         full screen on and off
    ESC       leave full screen (does NOT quit)
    Q         quit

------------------------------------------------------------------------------
Three speeds
------------------------------------------------------------------------------
This programme deliberately runs at three different rates, and keeping them
apart is the most important structural decision in the project.

  30 times a second   DRAWING. Pure arithmetic, never waits for anything.
  2 times a second    THINKING. The creature's feelings decay, the rules in
                      brain.metta decide what to express.
  once an evening     REMEMBERING. Every touch is kept. Nothing clears it.

The building is not running an animation with a few interactive bits bolted on.
It has an internal state that persists, a set of rules that reason about that
state in symbols, and a body that expresses whatever those rules decide. That
is the whole claim, and the three rates above are how it is kept honest -- the
part that reasons can never stall the part that draws.
"""

import os
import sys
import time
import random

import numpy as np
import pygame

from gbsim.display import Frame, Color

from living_field.field import Field, ROWS, COLS
from living_field.reaction import ReactionField
from living_field.worlds import WORLDS, BY_NAME, SOUNDING, blend
from living_field.patterns import PATTERNS
from living_field import ramps
from living_field.governor import Governor
from living_field.trueview import TrueView
from living_field.mirror import Mirror
from living_field.sensor import open_sensor
from living_field.creature import Creature
from living_field.brain import Brain
from living_field.surge import Surge
from living_field.tree import Tree
from living_field.weather import Weather
from living_field.autonomy import WeatherSeeder
from living_field.learner import AttentionLearner
from living_field.text import Ticker, weather_message
from living_field.control import Control
from living_field.demo import Director, SAY_WEATHER_AT
from living_field.race import Race, CREWS, finale, FINALE
from living_field.koc import KingOfCharles, SCHOOLS
from living_field.audio import Audio      # Spotify, if you prefer it
from living_field.music import Music

FPS = 30
BRAIN_HZ = 2.0            # how often it gets to think
TRANSITION_SECONDS = 4.0  # how long one world takes to become another


# ---------------------------------------------------------------------------
# THE FAST HALF -- turning a surface into 153 colours
# ---------------------------------------------------------------------------
def render(field, world, t, texture=None):
    """
    Take the state of the surface and produce a 17 x 9 x 3 picture, 0 to 1.

    The order matters. The resting colour is already bright enough to see, and
    breathing and crests scale it UP from there. An earlier version multiplied
    a dim colour by a dim brightness and the two small numbers compounded into
    near-black. Start bright, then modulate.
    """
    f = field.to_display()

    # The shape belonging to this world, plus whatever a person has done to it.
    h = f * world.gain * world.field_amount
    if texture is not None:
        h = h + texture
    h = np.clip(h, -1.0, 1.0)

    # Lift the faint stuff. A ripple that has climbed twenty storeys arrives at
    # a few percent of its original strength -- true to physics, and completely
    # invisible. This brings it back without blowing out the bright end, the
    # same way an eye does.
    h = np.sign(h) * (np.abs(h) ** world.response)

    # Breathing, TRAVELLING UP THE BUILDING rather than flashing the whole face
    # at once. Measured: a breath that moves together leaves every window at
    # exactly the same brightness, and a uniformly lit facade is not a creature,
    # it is a building with its lights on.
    rows = np.arange(ROWS, dtype=np.float32).reshape(-1, 1) / ROWS
    phase = world.breath_rate * t - rows * world.breath_travel
    breath = 1.0 + np.sin(2.0 * np.pi * phase) * world.breath_depth

    drift = 1.0 + world.drift_depth * np.sin(
        2.0 * np.pi * (0.021 * t + rows * 1.7)
        + 1.3 * np.cos(2.0 * np.pi * (0.013 * t - rows * 0.9)))

    # Colour: look the height up in this world's ramp, stretched onto the slice
    # the surface actually reaches so the best colours at the ends appear.
    mix = np.clip(0.5 + 0.5 * h, 0.0, 1.0)
    lo, hi = world.ramp_range
    mix = np.clip((mix - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    colour = ramps.sample(world.ramp, mix)

    boost = 1.0 + world.ripple_boost * np.clip(h, 0.0, 1.0)
    scale = (world.level * breath * drift * boost)[:, :, None]
    return np.clip(colour * scale, 0.0, 1.0)


class _TreeSurface:
    """
    Lets the tree be drawn by exactly the same code as every other surface.

    Everything in render() expects something with a to_display() that hands
    back a 17 x 9 picture. The tree keeps a growing structure instead of a
    field, so this thin wrapper gives it the same shape and nothing else in
    the renderer has to know the difference.
    """

    def __init__(self, tree):
        self.tree = tree
        self.t = 0.0
        self.weather = None

    def step(self, *_):
        pass                      # the tree grows on its own clock, not here

    def to_display(self):
        w = self.weather
        if w is None:
            return self.tree.to_display(self.t, wind=0.40)
        return self.tree.to_display(self.t, wind=w.wind, bias=w.wind_bias)

    def energy(self):
        return 0.0


def poke_both(field, reaction, row, col, world):
    """
    Touch both surfaces at once.

    They answer the same touch differently -- the wave field sends a ripple
    that travels and fades, the living skin plants a colony that grows and
    stays -- so whichever world the building moves to next already carries the
    mark of where somebody stood.
    """
    field.poke(row, col, world.poke_strength, world.poke_radius)
    reaction.poke(row, col, 0.95, 0.075)


def to_frame(rgb):
    """Hand the picture over in the exact shape the building expects."""
    frame = Frame()
    b = (rgb * 255.0).astype(np.uint8)
    for r in range(ROWS):
        for c in range(COLS):
            frame[r, c] = Color(int(b[r, c, 0]), int(b[r, c, 1]), int(b[r, c, 2]))
    return frame


def main():
    # One line is all it ever took. Give a room name and the same frames go to
    # the Green Building simulator as well as the window here:
    #
    #     ~/hack140/start plucky-eagle
    #
    room = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GB_ROOM", "")).strip()
    local = TrueView()
    if room:
        from gbsim.web import WebDisplay
        display = Mirror(local, WebDisplay(room))
    else:
        display = local
    field = Field()
    reaction = ReactionField()
    governor = Governor()
    sensor = open_sensor()

    creature = Creature()         # how it feels
    surge = Surge()               # the rare event people wait for
    tree = Tree()                 # the one the crowd grows together
    tree_surface = _TreeSurface(tree)

    # The real wind outside, if this machine can reach a weather feed.
    # Entirely optional: it never blocks, and with no network the tree
    # sways on the last cached reading or on calm defaults.
    weather = Weather()
    tree_surface.weather = weather

    # Grows the tree from the wind when nobody can touch anything.
    # This is what makes the piece complete with no physical object
    # in the plaza -- see autonomy.py.
    seeder = WeatherSeeder(weather)

    # The part that learns. The rules say what is appropriate; this
    # works out which of those actually holds people, at this site,
    # tonight -- and remembers it for next time.
    # Only learns if there is something to learn from.
    learner = AttentionLearner(sorted(BY_NAME.keys()),
                               enabled=sensor.available)

    # A page people can open on a phone and press. This is the interaction
    # channel that needs nothing in the plaza -- no object, no power, no
    # liability, and forty people can use it at once.
    #
    # Bound to this machine only unless GB_CONTROL_HOST says otherwise, because
    # opening it to a room should be a decision somebody makes on purpose.
    control = Control(host=os.environ.get("GB_CONTROL_HOST", "127.0.0.1"))

    # Runs the story on a clock for a demo. Everything underneath keeps
    # running for real; this only decides when.
    director = Director()

    # King of the Charles. Four crews, the room rows them, the winner
    # gets the building. Runs instead of the worlds while it is on.
    race = Race()
    race_won_at = None

    # The team's race, running in binam's worker. The admin panel starts it,
    # the cheer page feeds it, and this watches -- so the music and the
    # building follow whatever the admin does, without needing their own
    # buttons or a second race that disagrees with the first.
    koc = KingOfCharles(enabled=os.environ.get("GB_KOC", "1") != "0")
    koc_won_at = None

    # Words, so a stranger does not have to be told how to read it.
    ticker = Ticker()
    next_message = 20.0
    message_until = -1.0
    message_started = 0.0
    touches_at_choice = 0
    brain = Brain()               # how it decides, from brain.metta

    current = target = SOUNDING
    transition = 1.0
    forced = None
    startle_began = -1e9
    last_decision = ""
    last_learned = "nothing yet"
    auto = True
    next_ambient = 0.0
    next_think = 0.0

    # Your set, from the music/ folder. Local files rather than Spotify: no
    # network, no ads between tracks, no licensing question for a public
    # square, and the volume knob works live. audio.py still has the Spotify
    # path if you would rather use that for a rehearsal.
    music = Music(enabled=os.environ.get("GB_AUDIO", "1") != "0")
    # Deliberately NOT started here.
    #
    # "One control from the admin side" means the admin's Start button is what
    # starts the music. Beginning it at launch made that button a no-op -- the
    # set was already playing before anybody pressed anything, and there was no
    # way to tell from the room whether the control worked.
    #
    # P still starts it by hand if you want music while setting up.
    crowned = False
    mirror_matrix = os.environ.get("GB_MATRIX", "0") == "1"

    if control.available:
        print(f"touch page: {control.url}   (open it on a phone to grow branches)")
    if music.tracks:
        print(f"music     : {len(music.tracks)} track(s) from music/")
    if room:
        print(f"simulator : https://sundai.willsarg.com/{room}?view=river")

    start = time.perf_counter()
    last_frame = start
    running = True

    while running:
        frame_start = time.perf_counter()
        t = frame_start - start

        # Real elapsed time, not an assumed 1/30.
        #
        # The race used to be stepped with a hardcoded 1/30 of a second. When
        # the loop ran slower than thirty frames a second -- which it does the
        # moment a crowd is hammering the touch page -- the race quietly ran in
        # slow motion: speeds at maximum, boats crawling, and a forty-second
        # race that never finished. Anything that models the passing of time
        # has to be told how much time actually passed.
        dt = min(frame_start - last_frame, 0.2)      # cap, so a stall is not a jump
        last_frame = frame_start

        # ---- input ----------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                display.resize(event.size)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_ESCAPE:
                    # Escape means "get me out of full screen", which is what it
                    # means everywhere else. Only Q quits.
                    if display.is_fullscreen():
                        display.toggle_fullscreen()
                elif event.key == pygame.K_SPACE:
                    poke_both(field, reaction, 1.0, 0.5, current)
                    tree.plant(1.0, 0.5)
                    creature.touched(t, 1.0, 0.5)
                elif event.key == pygame.K_a:
                    auto = not auto
                elif event.key == pygame.K_f:
                    display.toggle_fullscreen()
                elif event.key == pygame.K_v:
                    display.cycle_mode()
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    display.scale_true(1.15)
                elif event.key == pygame.K_MINUS:
                    display.scale_true(1 / 1.15)
                elif event.key == pygame.K_s:
                    surge.trigger(t)         # fire the rare event on demand
                elif event.key == pygame.K_r:
                    race.start(t)
                    race_won_at = None
                    crowned = False
                elif event.key == pygame.K_d:
                    director.toggle(t)
                    if not director.running:
                        forced = None
                elif event.key == pygame.K_p:
                    if music.playing:
                        music.stop()
                    else:
                        music.start()
                elif event.key == pygame.K_m:
                    # Say the weather now. On its own it speaks for sixteen
                    # seconds out of every hundred and fifty, which is right
                    # for a building and wrong for a demo.
                    msg = weather_message(weather)
                    if msg:
                        forced = WORLDS[10]          # the forecast
                        ticker.set(msg)
                        message_started = t
                        message_until = t + ticker.duration()
                elif event.key == pygame.K_0:
                    forced = None            # let it decide for itself again
                elif event.key == pygame.K_t:
                    forced = WORLDS[9]       # the tree
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    forced = WORLDS[event.key - pygame.K_1]
            elif event.type == pygame.MOUSEBUTTONDOWN:
                spot = display.to_grid(event.pos)
                if spot is not None:
                    poke_both(field, reaction, spot[0], spot[1], current)
                    tree.plant(spot[0], spot[1])
                    creature.touched(t, spot[0], spot[1])

        # ---- the hardware, if there is any ----------------------------
        closeness, knocked = sensor.read()

        # The knobs, if the board has them.
        if sensor.volume is not None:
            music.volume(sensor.volume)
        music.tick(dt)
        if closeness > 0.15:
            field.poke(1.0, 0.5, 0.055 * closeness, 0.20)
            reaction.poke(1.0, 0.5, 0.05 * closeness, 0.10)
            creature.attended(t, closeness)
        if knocked:
            poke_both(field, reaction, 1.0, 0.5, current)
            tree.plant(1.0, 0.5, vigour=1.3)
            creature.touched(t, 1.0, 0.5, weight=1.3)

        # ---- the thinking half, twice a second ------------------------
        if t >= next_think:
            next_think = t + 1.0 / BRAIN_HZ
            creature.tick(t)
            facts = creature.facts(t)

            # Did the last expression hold anybody? Judge it, and learn.
            seen = learner.observe(t, closeness,
                                   len(creature.touches) - touches_at_choice)
            if seen:
                last_learned = f"{seen[0]} scored {seen[1]:.2f}"

            staged, fresh = director.update(t)
            if staged is not None:
                wanted = BY_NAME[staged]
                last_decision = "directed"
                if fresh and staged == "forecast" and director.elapsed >= SAY_WEATHER_AT:
                    msg = weather_message(weather)
                    if msg:
                        ticker.set(msg); message_started = t
                        message_until = t + ticker.duration()
            elif forced is not None:
                wanted = forced
                last_decision = "held"
            else:
                # The rules narrow it down to what is appropriate; the learner
                # picks the one that has been working.
                permitted = brain.allowed(facts)
                pick = learner.choose(permitted, t)
                wanted = BY_NAME[pick]
                last_decision = f"{len(permitted)} allowed -> {pick}"

            if wanted is not target and transition >= 1.0:
                current, target, transition = target, wanted, 0.0
                if forced is None:
                    learner.began(wanted.name.lower(), t, closeness)
                    touches_at_choice = len(creature.touches)
                if wanted.texture == "startle":
                    startle_began = t

        # ---- the drawing half, thirty times a second ------------------
        if transition < 1.0:
            transition = min(1.0, transition + (1.0 / FPS) / TRANSITION_SECONDS)
        eased = transition * transition * (3.0 - 2.0 * transition)
        world = blend(current, target, eased)

        if auto and t >= next_ambient:
            next_ambient = t + random.uniform(9.0, 22.0)
            field.poke(random.uniform(0.6, 1.0), random.uniform(0.25, 0.75),
                       0.09, world.poke_radius * 1.4)

        # Anybody who pressed the button on their phone.
        for _ in range(control.take()):
            col = random.uniform(0.15, 0.85)
            poke_both(field, reaction, 0.97, col, current)
            tree.plant(0.97, col)
            creature.touched(t, 0.97, col)

        # The weather plants branches when there is no crowd to.
        seeder.update(t, tree, touched_recently=(t - creature.last_touch_at) < 120.0)

        field.step(world.speed, world.damping)
        reaction.step()
        tree.grow(dt)                 # grows on wall-clock time
        tree_surface.t = t

        # What the people-aware patterns need to know.
        ctx = {
            "focus": creature.focus(t),
            "intensity": creature.arousal,
            "touches": list(creature.touches),
            "now": t,
            "age": t - startle_began,
            "forecast": weather.forecast_rows(),
        }

        # Crossfade the two worlds' patterns. A pattern is a picture, not a
        # number, so it cannot be averaged inside blend() -- but here both can
        # be drawn at once, which is what makes a transition look like one
        # thing becoming another.
        tex = (PATTERNS[current.texture](t * current.time_scale, ctx) * current.texture_amount
               * (1.0 - eased)
               + PATTERNS[target.texture](t * target.time_scale, ctx) * target.texture_amount
               * eased)

        # The rare event. Only when the building is calm -- interrupting
        # somebody's own interaction with a set piece would undo the thing
        # that makes this work.
        dim, glow = surge.update(t, calm=(creature.arousal < 0.35 and forced is None))
        if glow is not None:
            tex = tex + glow

        mix = world.substrate_mix
        if mix <= 0.01:
            rgb = render(field, world, t, tex)
        elif mix >= 0.99:
            rgb = render(reaction, world, t, tex)
        else:
            rgb = (render(field, world, t, tex) * (1.0 - mix)
                   + render(reaction, world, t, tex) * mix)

        # The tree is a structure, not a field, so it cannot be crossfaded with
        # one at the physics level. Draw it separately and dissolve between the
        # two pictures instead. blend() turns the is_tree flag into a number
        # between 0 and 1 during a transition, which is exactly the weight.
        tw = float(world.is_tree)
        if tw > 0.01:
            rgb = rgb * (1.0 - tw) + render(tree_surface, world, t, None) * tw

        if dim < 0.999:
            rgb = rgb * dim

        # Words over the forecast, now and then.
        #
        # Only over the forecast, and only every couple of minutes. The gradient
        # says what is coming to anybody who has learned to read it; the words
        # are for everybody else, and a building that talks constantly is noise.
        if world.name == "Forecast":
            if t >= next_message and not ticker.active and forced is None:
                msg = weather_message(weather)
                if msg:
                    ticker.set(msg)
                    message_started = t
                    message_until = t + ticker.duration()
                    next_message = t + 150.0
                else:
                    # No forecast yet -- it is still downloading. Try again
                    # shortly rather than going quiet for two and a half
                    # minutes, which is what happened the first time and made
                    # it look as though the text was simply not there.
                    next_message = t + 12.0
            if ticker.active and t < message_until:
                # Time SINCE THE MESSAGE STARTED, not clock time. The
                # ticker fades in and out over a fixed span and returns
                # nothing outside it, so handing it the wall clock meant
                # it was always already over.
                letters = ticker.render(t - message_started)
                if letters is not None:
                    bright = ramps.sample(world.ramp, np.full((ROWS, COLS), 0.97))
                    m = letters[:, :, None]
                    rgb = rgb * (1.0 - 0.85 * m) + bright * (0.85 * m)
            elif ticker.active:
                ticker.set("")

        # ---- the team's race, if the admin has started one ---------------
        for ev in koc.take_events():
            if ev == "started":
                music.start()          # the Start button starts the music
                koc_won_at = None
            elif ev == "stopped":
                music.stop()
            elif ev == "finished":
                music.crowning()       # ducks the set, rings the fanfare
                koc_won_at = t

        # ---- King of the Charles takes over the whole building ----------
        # Their race drives the building when it is on: same lanes, same
        # finale, positions straight from the worker rather than simulated
        # here. One race, not two that disagree.
        if koc.running or koc_won_at is not None:
            for i, school in enumerate(SCHOOLS):
                CREWS[i].pos = koc.progress.get(school, 0.0)
            if koc.running:
                rgb = race.render(t)
            else:
                age = t - koc_won_at
                lead = max(range(4), key=lambda i: CREWS[i].pos)
                rgb = finale(age, CREWS[lead], t)
                if age > FINALE + 3.0:
                    koc_won_at = None

        elif race.running or race_won_at is not None:
            for lane, n in enumerate(control.take_strokes()):
                if n:
                    race.row(lane, n)
            race.step(dt, t)

            if race.running:
                rgb = race.render(t)
            else:
                if race_won_at is None:
                    race_won_at = race.finished_at or t
                    if not crowned:
                        # Over the top of the music, not instead of it.
                        music.crowning()
                        crowned = True
                    ticker.set(f"{race.winner.short} WINS")
                    message_started = race_won_at + FINALE - 2.4
                    message_until = message_started + ticker.duration()
                age = t - race_won_at
                rgb = finale(age, race.winner, t)
                if age > FINALE + ticker.duration():
                    race_won_at = None          # back to being a building
                    race.reset()
                    ticker.set("")

            # The name, over the settling glow at the end.
            if race_won_at is not None and t >= message_started:
                letters = ticker.render(t - message_started)
                if letters is not None:
                    m = letters[:, :, None]
                    white = np.full((ROWS, COLS, 3), 0.95, dtype=np.float32)
                    rgb = rgb * (1.0 - 0.9 * m) + white * (0.9 * m)

        # The brightness knob, if there is one.
        #
        # Applied BEFORE the governor on purpose. Turn it all the way up in
        # front of somebody and the building still cannot pass its ceiling,
        # because the ceiling is downstream of the knob. That is a better
        # argument about safety than a paragraph about it.
        if sensor.bright is not None:
            rgb = rgb * (0.25 + 0.75 * sensor.bright)

        rgb = governor.apply(rgb)      # nothing reaches the windows unchecked

        # Mirror the tower onto the board's own grid, if one is plugged in.
        #
        # OFF by default. This writes ~100 bytes to the board ten times a
        # second, and it is the prime suspect for the board wedging: the sketch
        # stops responding, stops printing, and will not even accept an upload
        # until it is physically reset. A minimal sketch that never reads from
        # the host survives indefinitely; this one does not.
        #
        # It is a nice-to-have -- the miniature tower in your palm -- and not
        # worth a dead board mid-demo. GB_MATRIX=1 turns it back on.
        if mirror_matrix:
            sensor.send_matrix(rgb)

        ts = tree.stats()
        hw = "arduino" if sensor.available else "no arduino"
        if koc.running or koc_won_at is not None:
            board = "  ".join(f"{c.short} {c.pos*100:3.0f}%" for c in race.standings())
            staged_line = f"{koc.summary().upper()}   {board}"
        elif race.running:
            board = "  ".join(f"{c.short} {c.pos*100:3.0f}%" for c in race.standings())
            staged_line = f"KING OF THE CHARLES (local)   {board}"
        elif race_won_at is not None:
            staged_line = f"{race.winner.name.upper()} WINS"
        else:
            staged_line = director.status()
        display.label = (
            (staged_line + "   |   " if staged_line else "")
            + f"{world.name.upper()} - {world.subtitle}   |   "
            f"arousal {creature.arousal:.2f}  curiosity {creature.curiosity:.2f}  "
            f"fatigue {creature.fatigue:.2f}  remembers {len(creature.touches)}   |   "
            f"tree {ts['branches']}br/{ts['people']}p ({seeder.planted} wind, {control.total} phone)   |   "
            f"{weather.summary()}   |   "
            f"{brain.engine}: {last_decision}   |   learned: {learner.report()}   |   "
            f"{surge.phase() or hw}  "
            f"[1-9] force  [0] auto  [space] touch  [v] {display.mode_name()}  [q] quit")
        display.send(to_frame(rgb))

        # The building must never be sent frames faster than 30 a second.
        elapsed = time.perf_counter() - frame_start
        if elapsed < 1.0 / FPS:
            time.sleep(1.0 / FPS - elapsed)
        else:
            # Even when a frame overruns, hand the CPU over briefly. Without
            # this a run of slow frames never yields and the audio thread is
            # starved for as long as it lasts.
            time.sleep(0.001)

    koc.close()
    music.stop()
    sensor.close()
    weather.close()
    control.close()
    if hasattr(display, 'close'):
        display.close()
    pygame.quit()


if __name__ == "__main__":
    sys.exit(main())
