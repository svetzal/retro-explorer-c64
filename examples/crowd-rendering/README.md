# Draw eight moving grunts

Draw eight green figures in character RAM. Four pairs meet, overlap and separate.
A yellow pilot and two shots use hardware sprites over the same floor.
The paths repeat without player input.

## Choose the layer

| Objects | Layer | Cost in this example |
| --- | --- | --- |
| Eight grunts with the same ink | Standard character mode with RAM glyphs | Up to four cells per 8 by 8 figure |
| Pilot and two shots | Three hardware sprites | Three of the eight sprite slots |

## Find the example

1. At `present`, select the finished screen and glyph set. Write sprite positions for the same update.
2. At `prepare`, clear the cells that this page used on its previous pass.
   Draw all eight figures on the hidden page. Combine their dots wherever they share a cell.

These are the two marked parts of [main.asm](main.asm).
The rails, paths, pilot, shots and timer samples provide context.

## Run in VICE

From the starter folder, run:

```sh
uv run python scripts/c64.py run examples/crowd-rendering  # repeating crowd pass
```

Check the rendered pictures and timing:

```sh
uv run python scripts/c64.py check examples/crowd-rendering
```

All builds show the same animation. The variants select checkpoints at different times.
The timing build checks 63 intervals between updates and 64 preparation times.

## Sources

Commodore, *Commodore 64 Programmer's Reference Guide* (1982), resource `c64-prg`:
PDF 121–123 and 128–129 cover screen and glyph memory.
PDF 152–158 cover sprite data and position. PDF 169 describes the raster register.
PDF 348–350 describe CIA timer A.

See the [crowd rendering guide](../../guidance/techniques/crowd-rendering.md) for the measured limits and failure control.
