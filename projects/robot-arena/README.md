# Robot Arena

Build a Robotron-style game with WASD for movement and O, K, L and semicolon for fire.
The first experiment checks whether a player can move and fire together.

Open lab: movement-fire-keys

## Run

The project still contains the starter program. To run it from the repository root:

```sh
uv run python scripts/c64.py run projects/robot-arena
```

## Contract

- Owner request: use the two groups of keys from the CoCo game.
- Prototype choice: W, A, S and D move up, left, down and right.
- Prototype choice: O, K, L and semicolon fire up, left, down and right.
- Starter default: NTSC C64 with 64 KiB of RAM, VIC-II 6567 and SID 6581.
- Starter default: VICE x64sc with the ntsc model.
- Starter firmware: KERNAL 901227-03 revision 3, BASIC 901226-01 and character ROM 901225-01.
- Starter loader: VICE starts the PRG. Its BASIC line starts the machine code.

See the [target settings](../../guidance/starter/toolchain.md#target-tables).
