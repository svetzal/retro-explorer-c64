# Move sprites over a character arena

Use a character screen for the room and status line. Give each moving figure a hardware sprite.
On the NTSC C64, this lets a figure move by one display dot while the arena stays in place.
The [sprite motion example](../../examples/sprite-motion/README.md) shows a player, a grunt and a shot.

## Choose a sprite mode

A standard sprite has 24 dots across and 21 rows. It uses one ink and a transparent background.
A multicolour sprite has 12 colour pairs across. Each pair spans two display dots.
Its inks come from one individual register and two registers shared by all multicolour sprites.
Its position can still change by one display dot.

Source: Commodore, *Commodore 64 Programmer's Reference Guide* (1982), PDF 152–155 and 161, resource `c64-prg`.

For Arena Blaster we used the wide colour pairs for the CoCo silhouettes.
Each of the three shapes needs 64 aligned bytes, including one padding byte.
The example puts them at `$2000`, `$2040` and `$2080` in VIC bank zero.
With the screen at `$0400`, the first three sprite pointers start at `$07F8`.
Each pointer holds the shape offset within the bank divided by 64.
Source: *Programmer's Reference Guide*, PDF 152–153.

## Place the actors

Keep positions in pixels. For the default 40 by 25 display, add 24 to the playfield X coordinate and 50 to Y.
Write the low eight bits of X and the eight bits of Y to the sprite position registers.
Write the ninth X bit to the sprite's own bit in `$D010`.

Preserve the X bits of the other active sprites. The example builds the complete mask for its three known paths.
Source: *Programmer's Reference Guide*, PDF 157–161.

In the example, the player moves from hardware X 255 to 256 while the grunt stays beyond 255.
The player's X byte changes from 255 to zero. A missing ninth bit makes the player disappear at that crossing.
We disabled that bit in a control run. The screen memory still matched, but the rendered frame failed at the crossing.

## Pace the updates

Wait for raster line 252 after the playfield. Wait until the raster leaves that line before counting the next field.
Update all three positions every second field. The example uses two fields per update to match the CoCo game's cadence.
Source for the raster register: *Programmer's Reference Guide*, PDF 169.

The NTSC model in VICE 3.10 has 263 lines of 65 cycles per field (`src/c64/c64.h`).
Two fields therefore take 34,190 cycles. The timing build reads CIA timer A at 32 consecutive updates.
See *Programmer's Reference Guide*, PDF 348–350, for the timer registers.

## What the check shows

Run `uv run python scripts/c64.py check examples/sprite-motion` to repeat the measurement.
In NTSC VICE 3.10 the first five fields showed the initial position twice, the next position twice, then a third position.
The character screen stayed fixed. Across one pass the 31 update intervals ranged from 34,174 to 34,207 cycles.
The check allows one raster line of timing variation.

## Open questions

The measured load is three sprites on fixed paths. A full encounter adds keyboard input, collision checks and game rules.
Measure again under that load. Assess control feel during interactive play.
The host display, physical hardware, PAL timing and crowded levels need separate trials.
