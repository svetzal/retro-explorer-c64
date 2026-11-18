"""Encounter snapshots on the 40 by 25 text screen (c64-prg, PDF 395 and 401)."""

import numpy as np

# Each fixture describes a visible outcome at the configured checkpoint.
SCENES = {
    "northwest": ("DESTROY THE ROBOT", (19, 11), (30, 12), (21, 13)),
    "northeast": ("DESTROY THE ROBOT", (21, 11), (30, 12), (19, 13)),
    "southwest": ("DESTROY THE ROBOT", (19, 13), (30, 12), (21, 11)),
    "southeast": ("DESTROY THE ROBOT", (21, 13), (30, 12), (19, 11)),
    "slide": ("DESTROY THE ROBOT", (1, 11), (30, 12), None),
    "opposed": ("DESTROY THE ROBOT", (20, 12), (30, 12), None),
    "one-axis": ("DESTROY THE ROBOT", (21, 12), (30, 12), (21, 10)),
    "edge": ("DESTROY THE ROBOT", (1, 12), (30, 12), None),
    "replay": ("DESTROY THE ROBOT", (20, 12), (21, 12), None),
    "main": ("PRESS A CONTROL TO START", (20, 12), (30, 12), None),
    "strafe": ("DESTROY THE ROBOT", (19, 12), (30, 12), (19, 14)),
    "hit": ("ROBOT DOWN!  RELEASE, THEN PRESS TO PLAY", (20, 12), None, None),
    "chase": ("DESTROY THE ROBOT", (21, 12), (29, 12), None),
    "caught": ("CAUGHT!  RELEASE, THEN PRESS TO PLAY", (20, 12), None, (20, 11)),
}


def picture(variant):
    message, player, robot, shot = SCENES[variant]
    cells = bytearray(b" " * 1000)
    ink = bytearray([1] * 1000)

    def write(x, y, text, colour=1):
        start = 40 * y + x
        codes = bytes(ord(c) - 64 if c.isalpha() else ord(c) for c in text)
        cells[start : start + len(text)] = codes
        ink[start : start + len(text)] = bytes([colour] * len(text))

    write(0, 0, "ROBOT ARENA")
    write(0, 1, message)
    write(0, 24, "MOVE: W A S D       FIRE: O K L ;")
    for y in (2, 22):
        write(0, y, "#" * 40)
    for y in range(3, 22):
        write(0, y, "#")
        write(39, y, "#")
    write(*player, "+")
    if robot:
        write(*robot, "R", 2)
    if shot:
        write(*shot, "*", 7)
    return cells, ink


def expected_screen(variant):
    return bytes(picture(variant)[0])


def expected_colours(variant):
    return bytes(picture(variant)[1])


def expected_border():
    return 6


def expected_frame(chargen, variant):
    cells, ink = picture(variant)
    glyphs = np.frombuffer(bytes(chargen[:2048]), dtype=np.uint8).reshape(256, 8)
    codes = np.frombuffer(cells, dtype=np.uint8).reshape(25, 40)
    rows = glyphs[codes].transpose(0, 2, 1).reshape(200, 40)
    colours = np.frombuffer(ink, dtype=np.uint8).reshape(25, 40)
    return np.unpackbits(rows, axis=1) * colours.repeat(8, axis=0).repeat(8, axis=1)
