"""Level-one fixtures after two game updates. Positions use wide pixels across."""

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
    "clear": ("WAVE CLEAR!  SHOOT TO PLAY AGAIN", 10, 3, (80, 99), [], None),
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
    return bytes([14] * 1000)


def expected_frame(chargen, variant):
    tiles = np.frombuffer(expected_screen(variant), dtype=np.uint8).reshape(25, 40)
    glyphs = np.frombuffer(bytes(chargen[:2048]), dtype=np.uint8).reshape(256, 8)
    rows = glyphs[tiles].transpose(0, 2, 1).reshape(200, 40)
    image = np.where(np.unpackbits(rows, axis=1), 14, 6).astype(np.uint8)
    _, _, _, player, grunts, shot = SCENES[variant]
    actors = [(GRUNT, pos) for pos in grunts]
    if shot:
        back = ("Y..", "Y..", ".Y.", ".Y.", "..Y", "..Y")
        art = back if variant in ("strafe", "southeast") else tuple(row[::-1] for row in back)
        actors.insert(0, (art, shot))
    if player:
        actors.append((PLAYER, player))
    for art, (x, y) in actors:
        for dy, row in enumerate(art):
            for dx, c in enumerate(row):
                if c != ".":
                    col = 2 * (x + dx)
                    image[y + dy, col : col + 2] = {"G": 5, "R": 2, "Y": 7}[c]
    return image
