"""Non-mascot pixel art. One char = one window; '.' is transparent (window off).
Mascot drawings live in mascots.py."""

EGG_PALETTE = {
    "W": (200, 200, 190),  # shell
    "S": (163, 31, 52),    # spots (MIT red)
    "C": (40, 40, 40),     # crack
}

EGG = [
    ".WWW.",
    "WWSWW",
    "WWWWW",
    "SWWWW",
    "WWWSW",
    "WWWWW",
    ".WWW.",
]

# Cracks appear on the egg as the crowd gets closer to hatching it.
EGG_CRACKS = [(2, 1), (3, 2), (2, 3), (4, 3), (3, 4), (5, 1)]

HEART = ["B.B", "BBB", ".B."]
