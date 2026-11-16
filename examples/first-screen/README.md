# Put text on the screen

This example puts known text in known colours on the C64 text screen. It sets
the border and background colours, selects a character set, clears the screen
and writes two lines of text. Then it holds the picture.

The example does not use bitmap modes, sprites, scrolling, input, sound or
timed work. It does not move the screen or the character set to other
addresses. It uses the firmware's screen at `$0400` and the character ROM.

## Choose a character set

The C64 has two character sets in its character ROM. Only one set shows at a
time (PDF 395). Register `$D018` (53272) selects the set.

| Set | Name | `$D018` | Codes 1 to 26 | Codes 65 to 90 | Dots in the character ROM | Variant |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Upper case and graphics | 21 | A to Z | Graphics characters | Bytes 0 to 2047 | `main` |
| 2 | Upper and lower case | 23 | a to z | A to Z | Bytes 2048 to 4095 | `mixed-case` |

- Set 1 is the default. It has the graphics characters that games use for
  walls, boxes and bars. The firmware selects it, so the program does not
  write `$D018`.
- Set 2 is better for a game with much text, such as an adventure. It has no
  graphics characters at codes 65 to 90.
- Digits, the space and most punctuation have the same code in both sets
  (PDF 395-397).
- Add 128 to a code to show the character in reverse (PDF 395).
- The person can change the set with the Commodore and SHIFT keys (PDF 23).
  A game that must keep one set writes `$D018` itself.

The screen and its colours:

| Item | Address | Size | Values |
| --- | --- | --- | --- |
| Screen memory | `$0400` (1024) | 1000 bytes, 40 columns x 25 rows | Screen codes, not PETSCII (PDF 395-397) |
| Colour memory | `$D800` (55296) | 1000 values, 4 bits each | Colour codes 0 to 15 (PDF 402) |
| Border colour | `$D020` (53280) | 1 register | Colour code (PDF 342) |
| Background colour 0 | `$D021` (53281) | 1 register | Colour code (PDF 342) |

The cell at row r and column c is at `$0400 + 40 * r + c`. Its colour is at
the same offset from `$D800` (PDF 401-402). Some colour codes: 0 black,
1 white, 6 blue and 7 yellow (PDF 402).

## Set up the screen

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm). The
other code is context:

- The BASIC line at the start makes RUN start the program.
- The loop from `frame` to `shown` holds the picture. It passes the `shown`
  label once in each frame. The check stops the emulator at `shown`. A project
  replaces this loop with its own main loop.

The parts:

1. The addresses and the values: the screen, colour memory, the border and
   background registers, `$D018`, the colour codes and the text positions.
2. Set the border to blue and the background to black. In the `mixed-case`
   variant, write 23 to `$D018` to select set 2.
3. Write the space code (32) to the 1000 screen cells and white (1) to the
   1000 colour cells. Then copy the two lines of text into screen memory, and
   write yellow (7) to the colour cells of the second line.

The text in `main.asm` uses the 64tass screen encoding (`.enc "screen"`).
64tass changes each character to its screen code when it assembles. In that
encoding, `a` to `z` give the codes 1 to 26 and `A` to `Z` give the codes 65 to
90. Thus, the `main` variant writes its text in small letters, and set 1 shows
them as capital letters.

The example keeps the machine state that the firmware sets. The KERNAL
interrupt stays on. The example does not change the memory configuration or
the stack. The check shows that the interrupt does not change the screen
while the program runs.

Other ways: the KERNAL CHROUT routine at `$FFD2` prints PETSCII text and
moves the cursor (PDF 291, PDF 297 and PDF 398-399). It is slower, and it changes the
cursor position. A game that draws its own screen writes screen memory
directly.

## See and check each character set

Open a terminal in the starter folder. Copy one line and paste it to see that
variation in VICE. Close the window to stop it.

```sh
uv run python scripts/c64.py run examples/first-screen                       # set 1, upper case and graphics
uv run python scripts/c64.py run examples/first-screen --variant mixed-case  # set 2, upper and lower case
```

To see a variation on the NTSC target, add `--target c64-ntsc`.

To check both variations on both targets, paste this line:

```sh
uv run python scripts/c64.py check examples/first-screen
```

The check runs on the two targets in [c64.toml](c64.toml), `c64-ntsc` and
`c64-ntsc`. The [target tables](../../guidance/starter/toolchain.md#target-tables)
give their machine models and firmware.

On each target, the check compares five results with
[expected.py](expected.py):

- Screen memory.
- Colour memory.
- The border and background registers.
- VICE's rendered display window.
- The border around the display window. The check does not prove
the result on a monitor, a television or a physical C64.

## Sources

Read these pages before you change a value. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Commodore, *Commodore 64 Programmer's Reference Guide* (1982),
  resources.json id `c64-prg`:
  - PDF 23: the two character sets and the keys that change the set.
  - PDF 120: screen memory and colour memory.
  - PDF 124: the character ROM, and where each set is in it.
  - PDF 126-127: the dots of a character. Bit 7 is the leftmost dot.
  - PDF 135-136: background colour 0 shows where a dot is 0.
  - PDF 169: the raster register `$D012`.
  - PDF 342: the border and background registers.
  - PDF 395-397: screen codes, and `POKE 53272,21` and `POKE 53272,23`.
  - PDF 401-402: the screen and colour memory maps, and the colour codes.
  - PDF 466: the display window is raster lines 51 to 251.
- 64tass manual, <https://tass64.sourceforge.net/>: the BASIC loader and the
  screen encoding.

No cited page states which set the firmware selects at power-on. The check is
the evidence: the `main` variant passes with set 1. The control
`should_fail_only_the_frame_for_the_lower_case_character_set` in
[scripts/c64_spec.py](../../scripts/c64_spec.py) selects set 2 in the `main`
variant, and the rendered frame check fails.
