"""Boston / Cambridge schools and the colour each one paints on the tower."""

from tower.display import WHITE

SCHOOLS = {
    "mit": ("MIT", (163, 31, 52)),
    "harvard": ("Harvard", (165, 28, 48)),
    "bu": ("BU", (204, 0, 0)),
    "neu": ("Northeastern", (200, 16, 46)),
    "tufts": ("Tufts", (62, 142, 222)),
    "bc": ("Boston College", (138, 100, 20)),
    "berklee": ("Berklee", (230, 180, 0)),
    "wellesley": ("Wellesley", (0, 70, 200)),
    "emerson": ("Emerson", (160, 60, 220)),
    "olin": ("Olin", (0, 180, 200)),
    "umb": ("UMass Boston", (0, 90, 170)),
    "wit": ("Wentworth", (255, 140, 0)),
    "massart": ("MassArt", (255, 60, 160)),
    "suffolk": ("Suffolk", (240, 200, 40)),
    "other": ("Other", (140, 255, 140)),
}

# MIT and Harvard are both crimson on paper; on a building they need to be told apart.
DISPLAY_OVERRIDES = {"harvard": (120, 0, 200), "neu": WHITE}


def color(school_id):
    if school_id in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[school_id]
    return SCHOOLS.get(school_id, SCHOOLS["other"])[1]


def name(school_id):
    return SCHOOLS.get(school_id, SCHOOLS["other"])[0]
