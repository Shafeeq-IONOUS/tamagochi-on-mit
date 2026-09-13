"""
The version that needs nobody's permission.

A physical box in a public plaza is a much bigger ask than software. It means
liability, someone tripping over it, power in the open, weather, theft, and a
person standing beside it all evening. Software running on a display the
building already operates is a small ask; an object on the ground that strangers
touch is an institutional decision, and it is the one part of this project that
could be refused outright.

So the piece has to be complete without it.

This is what plants the tree when nobody can touch anything: the WEATHER does.
Every gust of wind that arrives grows a branch. Over an evening the building
carries a tree shaped by the night it actually stood in -- windy nights grow
wide, still nights grow tall and sparse.

That is not a consolation prize. For a building that houses the department of
atmospheric science, a tree grown by the weather is arguably the better idea.
And it means there are two separate asks instead of one:

    "run our software on the display"          <- easy yes, complete on its own
    "and give us a spot for a sensor"          <- upgrade, can be refused

with the fragile half unable to take the whole thing down with it.

If the box IS approved, both work at once: gusts and people both plant branches,
and the story becomes the tree the crowd grew.
"""

import random


class WeatherSeeder:
    """Grows the tree from the wind when there is nobody to grow it from."""

    # Roughly one branch every this many seconds at moderate wind. A still
    # night is slower and the tree stays sparse; a gale fills it faster.
    #
    # Tuned for a three-hour evening: a still night grows about twenty
    # branches, a breezy one seventy, a gale a hundred and twenty. An earlier
    # value planted five hundred and sixty, which is not a tree growing over an
    # evening, it is a hedge appearing in twenty minutes.
    BASE_INTERVAL = 130.0

    def __init__(self, weather=None, seed=0):
        self._rng = random.Random(seed)
        self.weather = weather
        self._next = 6.0
        self._planted = 0

    def update(self, t, tree, touched_recently):
        """
        Plant a branch if the wind says so.

        Stands aside the moment real people are involved: if somebody has
        touched the building in the last couple of minutes, the tree is theirs
        and the weather stops adding to it. A crowd's tree should be the
        crowd's, not diluted with wind.
        """
        if touched_recently:
            self._next = max(self._next, t + 45.0)
            return False
        if t < self._next:
            return False

        wind = self.weather.wind if self.weather else 0.35

        # Harder wind, more branches -- but never a flood.
        interval = self.BASE_INTERVAL / max(0.25, wind * 1.6)
        self._next = t + self._rng.uniform(interval * 0.6, interval * 1.5)

        # Where the wind is coming from decides which side grows. A building
        # that spends the night in a westerly ends up with a tree leaning east,
        # which is what a real tree on an exposed site actually does.
        bias = self.weather.wind_bias if self.weather else 0.0
        # A lean, not a landslide. At 0.28 a steady westerly grew the whole
        # tree into the right-hand four columns and left the rest of the
        # building empty -- a real tree leans into the wind, it does not grow
        # only one side of itself.
        if self._planted == 0:
            # The trunk goes in the middle of the building, always. Left to
            # chance it landed wherever the first draw fell, and a tree rooted
            # in column seven leaves half the facade empty for the rest of the
            # night. The crown can lean; the trunk should not.
            col = 0.5 + self._rng.uniform(-0.04, 0.04)
        else:
            centre = 0.5 + 0.11 * bias
            col = min(0.95, max(0.05, self._rng.gauss(centre, 0.28)))

        # Gusts mostly catch the top of a tree, so later branches start higher.
        row = 0.97 if self._planted < 1 else self._rng.uniform(0.55, 0.95)

        tree.plant(row, col, vigour=0.7 + 0.6 * wind)
        self._planted += 1
        return True

    @property
    def planted(self):
        return self._planted
