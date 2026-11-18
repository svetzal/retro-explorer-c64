"""Idle screen in the default character set (c64-prg, PDF 126, 395 and 401)."""

import numpy as np


def expected_screen():
    lines = ("MOVE        FIRE", "W A S D     O K L ;")
    text = "".join(line.ljust(40) for line in lines).ljust(1000)
    return bytes(ord(c) - 64 if c.isalpha() else ord(c) for c in text)


def expected_frame(chargen):
    glyphs = np.frombuffer(bytes(chargen[:2048]), dtype=np.uint8).reshape(256, 8)
    cells = np.frombuffer(expected_screen(), dtype=np.uint8).reshape(25, 40)
    # Arrange the eight rows of each glyph in raster order before expanding dots.
    rows = glyphs[cells].transpose(0, 2, 1).reshape(200, 40)
    return np.unpackbits(rows, axis=1)  # white (1) on black (0)
