# Move sprites across a character boundary

Three sprites move over a fixed character arena. The player moves down and right while a shot travels up and left.
A grunt moves left. The paths repeat so you can watch the same crossing. This example has no game controls.

## Choose the artwork

| Object | Representation | Reason |
| --- | --- | --- |
| Arena and status line | Standard character screen | The playfield stays fixed as actors pass over it. |
| Player and grunt | Multicolour sprites | Two-dot colour pairs suit the wide pixels of the original figures. |
| Shot | Multicolour sprite with one ink | It follows its own path with the same position controls as the actors. |

## Find the example code

The three marked parts of [main.asm](main.asm) show how to:

1. Set the shape pointers and colours for three sprites.
2. Change positions after every second NTSC field.
3. Write the pixel positions and their ninth X bits.

The arena, silhouettes and repeatable paths provide context. The field counter selects a checkpoint.
The timing build also samples a CIA timer at each update.

## Run and check

From the starter folder, run the repeating pass:

```sh
uv run python scripts/c64.py run examples/sprite-motion  # three moving sprites
```

Check the first five fields and the timing of a full pass:

```sh
uv run python scripts/c64.py check examples/sprite-motion
```

Each variant samples the same animation. The check compares the character screen and the rendered picture.
The final variant also checks the spacing of 32 updates.

## Sources

Commodore, *Commodore 64 Programmer's Reference Guide* (1982), resource `c64-prg`:
PDF 152–155 covers sprite data and colours. PDF 157–161 covers position.
PDF 169 describes the raster register. PDF 348–350 describes CIA timer A.
The [sprite motion guide](../../guidance/techniques/sprite-motion.md) gives the results and limits.
