# Read movement and fire keys together

For independent movement and fire, read the current state of each key.
Read all eight controls on every scan. Keep scanning after the first pressed key.
Arena Blaster uses W, A, S and D for movement, and O, K, L and semicolon for fire.

## How the scan works

The C64 keyboard has eight columns and eight rows.
CIA 1 port A at `$DC00` selects columns. Port B at `$DC01` reads rows.
The direction registers for these ports are `$DC02` and `$DC03`.
Source: Commodore, *Commodore 64 Programmer's Reference Guide* (1982), PDF 113 and 347–348, resource `c64-prg`.

The [example](../../examples/held-keys/README.md) uses the following procedure:

1. Give the scanner control of CIA 1. The example masks IRQs to keep the firmware keyboard scan out of the loop.
2. Set port A for output and port B for input.
3. Write the column value for one key to port A.
4. Read port B. Apply the row mask for that key. Zero means pressed.
5. Record the result for that key. Repeat for the remaining keys.

| Key | Direction | Port A value | Port B mask |
| --- | --- | --- | --- |
| W | Move up | `$FD` | `$02` |
| A | Move left | `$FD` | `$04` |
| S | Move down | `$FD` | `$20` |
| D | Move right | `$FB` | `$04` |
| O | Fire up | `$EF` | `$40` |
| K | Fire left | `$EF` | `$20` |
| L | Fire down | `$DF` | `$04` |
| Semicolon | Fire right | `$BF` | `$04` |

We derived the masks from the key coordinates in the VICE 3.10 distribution, file `C64/gtk3_sym.vkm`.
Clear the selected column bit in an eight-bit value of all ones. Set only the selected row bit in the mask.
A and L share a row bit. Selecting their columns separately distinguishes them.

The two tables use 16 bytes and the loop reads one key at a time.
The display updates on each scan. A game can use the same readings once per game update.
A game that needs IRQs must arrange for one scanner to control the ports during each scan.
The example leaves IRQs masked for its whole run.

## Evidence and limits

On 17 November 2026, Stacey tested the eight keys in VICE 3.10 with the NTSC C64 model.
She saw the indicators respond to individual keys and combinations.
The report covers the combinations she tried. Their individual release orders remain open.

To repeat the observation, open the example. Hold A, add L, then release A while holding L.
Only L should stay lit. Release L and check that both stars disappear.

For coverage of all 16 movement and fire pairs, repeat with each movement key and each fire key.
Use a single key as a control. Only its own star should appear.

The example check compares the idle screen memory and rendered display with the expected labels and blank indicators.
The starter can send text into the firmware buffer. Held switches still need a test in the emulator window.

## Open questions

Physical C64 keyboards and other host keymaps need their own trials.
Test larger combinations separately if a game needs diagonal movement and fire together.
