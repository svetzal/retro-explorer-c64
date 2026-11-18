from itertools import pairwise

import numpy as np

SAMPLES = {"main": 0, "partial": 13, "touch": 16, "separate": 29, "turn": 32, "timing": 64}
GRUNT = (
    ".######.",
    "##.##.##",
    "########",
    "#.#..#.#",
    ".######.",
    "..####..",
    ".##..##.",
    "##....##",
)
PILOT = ("...##...", "..####..", ".######.", "##.##.##", "..####..", "..#..#..", ".##..##.")


def expected_frame(chargen, variant):
    phase = SAMPLES[variant] % 64
    travel = min(phase, 64 - phase)
    image = np.full((200, 320), 6, np.uint8)
    image[8:16, :] = image[192:200, :] = 5

    def draw(x, y, rows, colour):
        for dy, row in enumerate(rows):
            for dx, pixel in enumerate(row):
                if pixel == "#":
                    image[y + dy, x + dx] = colour

    for pair in range(4):
        x, y = (46, 90, 134, 244)[pair], 84 + 2 * pair + travel // 2
        draw(x + travel, y, GRUNT, 5)
        draw(x + 32 - travel, y + 3, GRUNT, 5)
    draw(189 - phase, 98, ("####", "####"), 2)
    draw(76 + 2 * phase, 92, ("####", "####"), 1)
    draw(121 + phase, 89, PILOT, 7)
    return image


def verify_state(state, variant):
    assert state.io[0x15] == 7, "one pilot and two shot sprites"
    if variant != "timing":
        return "three enabled sprites"

    def times(prefix):
        lo, hi = (state.symbols[prefix + s] for s in ("_lo", "_hi"))
        return [state.ram[lo + i] + 256 * state.ram[hi + i] for i in range(64)]

    starts, ends = times("clock"), times("finish")
    gaps = [(a - b) % 65536 for a, b in pairwise(starts[1:] + starts[:1])]
    costs = [(a - b) % 65536 for a, b in zip(starts, ends)]
    assert all(abs(dt - 34190) < 65 for dt in gaps), (min(gaps), max(gaps), max(costs))
    assert max(costs) < 17095, max(costs)
    return f"{len(gaps)} update intervals {min(gaps)}..{max(gaps)} cycles; preparation {min(costs)}..{max(costs)} cycles"
