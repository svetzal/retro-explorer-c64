"""Draw the reference silhouettes at their specified positions, independent of PRG data."""

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
SHOT = ("Y..", "Y..", ".Y.", ".Y.", "..Y", "..Y")


def expected_screen():
    cells = bytearray([32] * 1000)
    title = "ARENA BLASTER"
    cells[1 : 1 + len(title)] = bytes(ord(c) - 64 if c != " " else 32 for c in title)
    for row in range(1, 25):
        for col in range(40):
            if row in (1, 24) or col in (0, 39):
                cells[row * 40 + col] = 160
    return bytes(cells)


def expected_frame(chargen, variant):
    field = 1 if variant == "main" else int(variant.split("-")[1])
    step = ((field - 1) // 2) % 32
    tiles = np.frombuffer(expected_screen(), dtype=np.uint8).reshape(25, 40)
    glyphs = np.frombuffer(bytes(chargen[:2048]), dtype=np.uint8).reshape(256, 8)
    dots = np.unpackbits(glyphs[tiles].transpose(0, 2, 1).reshape(200, 40), axis=1)
    picture = np.where(dots, 14, 6).astype(np.uint8)
    for art, x, y in (
        (PLAYER, 231 + step, 79 + step),
        (GRUNT, 282 - step, 55),
        (SHOT, 226 - 2 * step, 77 - 2 * step),
    ):
        for dy, row in enumerate(art):
            for dx, pixel in enumerate(row):
                if pixel != ".":
                    left = x + dx * 2
                    picture[y + dy, left : left + 2] = {"Y": 7, "R": 2, "G": 5}[pixel]
    return picture


def verify_state(state, variant):
    if variant != "field-65":
        assert state.io[0x15] & 7 == 7, "all three sprites must be enabled"
        return "three active sprites"
    lo = state.symbols["time_lo"]
    hi = state.symbols["time_hi"]
    times = [state.ram[lo + i] | state.ram[hi + i] << 8 for i in range(32)]
    gaps = [(a - b) % 65536 for a, b in pairwise(times)]
    # VICE 3.10 src/c64/c64.h: 263 lines of 65 cycles for the NTSC model.
    assert all(abs(gap - 2 * 263 * 65) < 65 for gap in gaps), gaps
    return f"{len(gaps)} update gaps, {min(gaps)} to {max(gaps)} cycles"
