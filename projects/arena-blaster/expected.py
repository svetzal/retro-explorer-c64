"""Expected wave snapshots. Horizontal positions use double-width pixels."""

from itertools import pairwise

import numpy as np

PLAYER = (
    "..YY..",
    "..YY..",
    ".RRRR.",
    "Y.RR.Y",
    "YRRRRY",
    "..RR..",
    "..RR..",
    ".Y..Y.",
    ".Y..Y.",
    "YY..YY",
)
GRUNT = (
    ".GGGG.",
    "GRGGRG",
    "GGGGGG",
    ".G..G.",
    "GGGGGG",
    "G.GG.G",
    "G.GG.G",
    "..GG..",
    ".G..G.",
    "GG..GG",
)
START = [(18, 34), (136, 48), (16, 160), (140, 153)]
CHASE = [(19, 36), (135, 50), (17, 158), (139, 151)]
WAVE_TWO = START + [(46, 43), (113, 164), (51, 152), (104, 34)]
WAVE_TWO_MOVED = CHASE + [(47, 45), (112, 162), (52, 150), (103, 36)]
# Banner, score, lives, player, grunts, shot
SCENES = {
    "main": ("SHOOT TO START", 0, 3, None, [], None),
    "start": ("LEVEL 1   SHOOT THE GRUNTS", 0, 3, (80, 99), START, None),
    "strafe": ("LEVEL 1", 0, 3, (76, 91), CHASE, (88, 115)),
    "respawn": ("LEVEL 1   SHOOT THE GRUNTS", 0, 2, (80, 99), [(80, 99), *START[1:]], None),
    "northeast": ("LEVEL 1", 0, 3, (84, 91), CHASE, (76, 115)),
    "southwest": ("LEVEL 1", 0, 3, (76, 107), CHASE, (88, 91)),
    "southeast": ("LEVEL 1", 0, 3, (84, 107), CHASE, (76, 91)),
    "opposed": ("LEVEL 1", 0, 3, (80, 99), CHASE, None),
    "slide": ("LEVEL 1", 0, 3, (4, 91), [(17, 36), (135, 50), (15, 158), (139, 151)], None),
    "hit": ("LEVEL 1", 10, 3, (80, 99), CHASE[1:], None),
    "bonus": ("LEVEL 1", 1000, 4, (80, 99), CHASE[1:], None),
    "clear": ("LEVEL 2   HOLD TWO KEYS FOR DIAGONALS", 10, 2, (80, 99), WAVE_TWO, None),
    "crowd-timing": (
        "LEVEL 2",
        0,
        3,
        (4, 99),
        [(max(4, x - 15), y + min(30, abs(99-y)) * (1 if y < 99 else -1)) for x, y in WAVE_TWO],
        None,
    ),
    "crowd": ("LEVEL 2", 0, 3, (76, 91), WAVE_TWO_MOVED, (88, 115)),
    "victory": ("WAVE CLEAR!  SHOOT TO PLAY AGAIN", 10, 3, (80, 99), [], None),
    "crowd-respawn": (
        "LEVEL 2   HOLD TWO KEYS FOR DIAGONALS",
        0,
        2,
        (80, 99),
        [(80, 99), *WAVE_TWO[1:]],
        None,
    ),
    "caught": ("CAUGHT!", 0, 3, (80, 99), [(80, 99), *START[1:]], None),
    "game-over": ("GAME OVER", 0, 0, (80, 99), [(80, 99), *START[1:]], None),
}


def expected_screen(variant):
    message, score, lives, *_ = SCENES[variant]
    text = f"ARENA BLASTER      {score:06}      LIVES {lives}".ljust(40) + message.ljust(40)
    cells = bytearray([32] * 1000)
    cells[:80] = bytes(ord(c) - 64 if c.isalpha() else ord(c) for c in text)
    for y in range(2, 24):
        for x in range(40):
            if y in (2, 23) or x in (0, 39):
                cells[y * 40 + x] = 160
    return bytes(cells)


def expected_border():
    return 0


def expected_colours():
    colours = np.full((25, 40), 14, np.uint8)
    colours[3:23, 1:39] = 5
    return colours.tobytes()


def draw_crowd(image, grunts):
    shape = (
        ".######.",
        "##.##.##",
        "########",
        "#.#..#.#",
        ".######.",
        "..####..",
        ".##..##.",
        "##....##",
    )
    for x, y in grunts:
        for dy, row in enumerate(shape):
            for dx, c in enumerate(row):
                if c == "#":
                    image[y + dy, 2 * x + dx] = 5


def draw_sprites(image, actors):
    for art, (x, y) in actors:
        for dy, row in enumerate(art):
            for dx, c in enumerate(row):
                if c != ".":
                    col = 2 * (x + dx)
                    image[y + dy, col : col + 2] = {"G": 5, "R": 2, "Y": 7}[c]


def expected_frame(chargen, variant):
    tiles = np.frombuffer(expected_screen(variant), dtype=np.uint8).reshape(25, 40)
    glyphs = np.frombuffer(bytes(chargen[:2048]), dtype=np.uint8).reshape(256, 8)
    rows = glyphs[tiles].transpose(0, 2, 1).reshape(200, 40)
    image = np.where(np.unpackbits(rows, axis=1), 14, 6).astype(np.uint8)
    _, _, _, player, grunts, shot = SCENES[variant]
    actors = [(GRUNT, pos) for pos in grunts]
    if SCENES[variant][0].startswith("LEVEL 2"):
        actors = []
        draw_crowd(image, grunts)
    if variant == "crowd-timing":
        for shot_x in range(18, 127, 12):
            image[102:104, 2*shot_x:2*shot_x+2] = 5
    if shot:
        x, y = shot
        y &= ~1
        image[y:y+2, 2*x:2*x+2] = 5
    if player:
        actors.append((PLAYER, player))
    draw_sprites(image, actors)
    return image


def verify_state(state, variant):
    if variant != "crowd-timing":
        level = 2 if variant in ("clear", "crowd", "victory", "crowd-respawn") else 1
        assert state.ram[state.symbols["level"]] == level
        return f"level {level}"

    def samples(name):
        start = state.symbols[name]
        return state.ram[start : start + 31]

    times = [lo + 256 * hi for lo, hi in zip(samples("time_lo"), samples("time_hi"))]
    intervals = [(a - b) % 65536 for a, b in pairwise(times)]
    assert all(abs(dt - 34190) < 65 for dt in intervals), intervals
    return f"30 game updates: {min(intervals)} to {max(intervals)} NTSC cycles"
