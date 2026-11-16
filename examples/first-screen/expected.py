"""Independent model of the first screen: screen memory, colour memory and the picture.

Written from the README's request and the Commodore 64 Programmer's Reference
Guide (resources.json: c64-prg), not from main.asm or a capture. PDF page numbers.
"""

import numpy as np

COLUMNS, ROWS = 40, 25  # 1000 cells from 1024 to 2023, 40 to a row (PDF 120, PDF 401)
CELL = 8  # each character is an 8 x 8 grid of dots (PDF 126)

# The requested picture: the text, where it starts, and its colour.
BORDER, BACKGROUND = "blue", "black"
LINES = {
    "main": (("HELLO, COMMODORE 64!", 11, 10, "white"), ("FIRST SCREEN", 13, 14, "yellow")),
    "mixed-case": (("Hello, Commodore 64!", 11, 10, "white"), ("First screen", 13, 14, "yellow")),
}
# The character set of each variant, and where its dots start in the character ROM:
# set 1 (upper case and graphics) in the first 2048 bytes, set 2 (upper and lower
# case) in the next 2048 bytes (PDF 124, PDF 126).
CHARACTER_SET = {"main": 1, "mixed-case": 2}
SET_BYTES = 2048
TEXT_COLOUR = "white"  # every other cell; a space shows no dots

# Colour codes for screen and colour memory (PDF 402).
COLOUR_CODES = {"black": 0, "white": 1, "blue": 6, "yellow": 7}


def screen_code(character: str, character_set: int) -> int:
    """Screen display codes (Appendix B, PDF 395-397)."""
    if character_set == 1 and "A" <= character <= "Z":
        return ord(character) - ord("A") + 1  # set 1: A is 1 ... Z is 26
    if character_set == 2 and "a" <= character <= "z":
        return ord(character) - ord("a") + 1  # set 2: a is 1 ... z is 26
    if character_set == 2 and "A" <= character <= "Z":
        return ord(character) - ord("A") + 65  # set 2: A is 65 ... Z is 90
    if "0" <= character <= "9":
        return 48 + int(character)  # 0 is 48 ... 9 is 57
    return {" ": 32, "!": 33, ",": 44}[character]


def expected_screen(variant: str) -> bytes:
    character_set = CHARACTER_SET[variant]
    cells = bytearray([screen_code(" ", character_set)] * COLUMNS * ROWS)
    for text, row, column, _ in LINES[variant]:
        start = row * COLUMNS + column  # row starts 1024, 1064, ... (PDF 401)
        cells[start : start + len(text)] = bytes(screen_code(c, character_set) for c in text)
    return bytes(cells)


def expected_colours(variant: str) -> bytes:
    """Colour memory, one value for each cell, in the same order (PDF 120, PDF 402)."""
    cells = bytearray([COLOUR_CODES[TEXT_COLOUR]] * COLUMNS * ROWS)
    for text, row, column, colour in LINES[variant]:
        start = row * COLUMNS + column
        cells[start : start + len(text)] = bytes([COLOUR_CODES[colour]] * len(text))
    return bytes(cells)


def verify_state(state) -> str:
    """Border 53280 ($D020) and background 0 53281 ($D021) (PDF 342).

    state.io holds $D000-$DFFF. Only the low 4 bits hold the colour: the guide reads
    the border with PEEK(53280) AND 15 (PDF 88).
    """
    border, background = state.io[0x20] & 15, state.io[0x21] & 15
    assert border == COLOUR_CODES[BORDER], f"border colour {border}, expected {BORDER}"
    assert background == COLOUR_CODES[BACKGROUND], (
        f"background colour {background}, expected {BACKGROUND}"
    )
    return f"border {BORDER} and background {BACKGROUND} registers"


def expected_border() -> int:
    return COLOUR_CODES[BORDER]


def expected_frame(chargen: bytes, variant: str) -> np.ndarray:
    """The 320 x 200 display window as colour codes.

    A character's dots are the 8 bytes at screen code x 8 in its character set,
    one byte for each row, with a 1 bit for a dot (PDF 126-127). The leftmost dot
    is bit 7: the "A" pattern 00011000 (PDF 127). A dot shows the cell's colour
    memory value, other positions show background 0 (PDF 135-136).
    The main build keeps the character set that the firmware selects at power-on.
    The model expects set 1 there. No cited page states the power-on set; the
    rendered check is the evidence, and the lower-case control in
    scripts/c64_spec.py fails when the set is wrong.
    """
    screen, colours = expected_screen(variant), expected_colours(variant)
    dots = chargen[(CHARACTER_SET[variant] - 1) * SET_BYTES :]
    picture = np.full((ROWS * CELL, COLUMNS * CELL), COLOUR_CODES[BACKGROUND], dtype=np.uint8)
    for cell, code in enumerate(screen):
        top, left = (cell // COLUMNS) * CELL, (cell % COLUMNS) * CELL
        for y in range(CELL):
            row = dots[code * CELL + y]
            for x in range(CELL):
                if row & (0x80 >> x):
                    picture[top + y, left + x] = colours[cell]
    return picture
