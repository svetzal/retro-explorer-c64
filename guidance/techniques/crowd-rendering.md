# Draw a crowd with character graphics

For a room with eight grunts of the same colour, give the grunts a shared character layer.
Keep the hardware sprites for actors that need their own colours and shapes.
The [working example](../../examples/crowd-rendering/README.md) runs on the NTSC C64 model in VICE.

## Build the hidden page

Keep two screens and two RAM character sets in VIC bank zero.
One screen and its glyphs stay visible while the CPU builds the other pair.
The upper four bits of `$D018` select the screen. Bits 1 to 3 select the character set.
Colour RAM stays at `$D800` for both screens.
Source: Commodore, *Commodore 64 Programmer's Reference Guide* (1982), PDF 121–123 and 128–129, resource `c64-prg`.

| Page | Screen | Character set | Value written to `$D018` |
| --- | --- | --- | --- |
| A | `$0400` | `$3000` | `$1C` |
| B | `$0C00` | `$3800` | `$3E` |

Each screen needs its own sprite pointers in its last eight bytes.
The example sets both tables during setup. The sprite shapes start at `$2000`.
Source: *Programmer's Reference Guide*, PDF 152–153.

Our renderer uses code 0 for the floor and code 1 for the rails.
Keep the moving footprints on floor cells. This version clears used cells back to floor.
A room with scenery inside the play area would need to restore that scenery.

1. Clear the screen cells listed for the hidden page. Each page keeps its own list.
2. Take the low three bits of each pixel coordinate. They select one of 64 shifts of the grunt shape.
3. Split that shape into four character-sized parts. On an empty cell, allocate a glyph and copy the first part that touches it.
4. If another part touches that cell, combine the rows with bitwise OR. A transparent dot then preserves any grunt ink already there.
5. After the playfield, write the new page selection and the sprite positions for that update. Repeat with the other page.

The renderer stores 2,048 bytes of shifted shapes for one 8 by 8 silhouette.
Eight grunts can touch up to 32 cells per page. The two lists use 128 bytes for cell addresses.
All eight grunts share green ink. Where two silhouettes cover the same dot, that dot stays green.
Drawing different enemy colours in one cell needs another design.

## Check the result

Run `uv run python scripts/c64.py check examples/crowd-rendering`.
The expected picture draws eight individual figures at their pixel positions.
It also draws the pilot and shots. It does not use the renderer's RAM glyphs.
The checkpoints cover partial overlap, crossing, separation, reversal and a repeat after two page swaps or more.
One pair crosses X 255 to exercise the upper X bit.

The overlap control replaces the OR instruction at `source` with a NOP in a test copy.
At the closest crossing, the rendered comparison found 108 wrong pixels.
The separate-position check still passed. This control distinguishes a broken overlap from broken movement.

## Timing and scope

In VICE 3.10 the NTSC model has 263 lines of 65 cycles each (`src/c64/c64.h`).
One field takes 17,095 cycles. The example presents a new page every two fields, about 30 times per second.
The loop must finish its preparation before the next field boundary.
CIA timer A measures the intervals in emulated CPU cycles. Source: *Programmer's Reference Guide*, PDF 348–350.

On the measured pass, 63 intervals ranged from 34,184 to 34,205 cycles.
Preparing the hidden page took 11,742 to 12,600 cycles.
That left at least 4,495 cycles before the first field deadline on this pass.
Clearing the entire hidden screen in the first trial missed that deadline.

These measurements cover eight grunts on fixed paths, one pilot and two shots.
Measure pursuit, input, collisions and the status display in the game.
Larger crowds, multicolour enemies, PAL and physical hardware remain open.

## Draw ten shots with the same ink

Our adaptation draws a two-by-two square at even pixel coordinates.
The square fits in one cell at every position. Ten shots increase the limit from 32 to 42 cells per page.
The two address lists need 40 more bytes in total.

Draw the grunts first. Allocate a clear glyph for a shot on empty floor.
Reuse the glyph when the cell already contains ink.
Combine the two shot rows with the existing rows using bitwise OR.
Where both shapes cover a pixel, they share its colour.

Run the crowd example check above. The shot variants compare the whole image during a crossing and after separation.
The timing variant took 15,233 to 16,138 cycles to prepare the hidden page in NTSC VICE.
Only the pilot used a hardware sprite. These times cover scripted paths.

For a visual trial, watch the green dots cross the grunts with the `shot-crossing` variant.
The Arena Blaster owner could follow the dots in the interactive trial.
Individual pixels have the same colour where the shapes overlap.

The [game check](../../projects/arena-blaster/README.md#check-the-two-waves) also covers collisions and pursuit.
Give movement and collisions one field. Use the next field to prepare the hidden page.
