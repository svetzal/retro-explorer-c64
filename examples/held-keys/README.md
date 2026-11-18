# Read held keys

Read eight switches in the C64 keyboard matrix. A star appears under each held key.
The example covers input only. The labels and stars make the input visible.

## Choose the input method

| Need | Method |
| --- | --- |
| Read movement and fire at the same time | Read each matrix switch on every scan. |
| Read typed text | Read characters from the firmware keyboard buffer. |

## Find the example code

The three marked parts of [main.asm](main.asm) implement the scan:

1. At startup, mask IRQs and set the CIA port directions. This prevents the firmware scan from changing the column selection.
2. At `scan`, select the column and read the row bit. Zero means pressed.
3. At `select` and `sense`, find the two eight-byte tables for the movement and fire keys.

The loader, labels and stars provide display context. Each indicator uses one character cell.

## Run the example

From the starter folder, run:

```sh
uv run python scripts/c64.py run examples/held-keys  # NTSC keyboard scan
```

Hold A and L together. Look for a star under each key.
Release A. Only the L star should remain. Release L. Both indicators should be blank.

Check the idle screen from the starter folder:

```sh
uv run python scripts/c64.py check examples/held-keys
```

The check compares all 1000 screen cells and the 320 by 200 pixel display.
Use the window to test held keys and release order.

## Sources

Commodore, *Commodore 64 Programmer's Reference Guide* (1982), resource `c64-prg`:
PDF 113 and 347–348 describe the keyboard ports. PDF 395 and 401 give the screen codes and layout.
The VICE 3.10 keymap `C64/gtk3_sym.vkm` gives the switch coordinates.
The [technique guide](../../guidance/techniques/held-keys.md) gives the masks and the limits of the test.
