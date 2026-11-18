# Arena Blaster

Build a Robotron-style game with WASD for movement and O, K, L and semicolon for fire.
Use the [keyboard scan](../../guidance/techniques/held-keys.md) to read movement and fire independently.

## Run

From the repository root, run:

```sh
uv run python scripts/c64.py run projects/arena-blaster
```

You are the white plus sign. The red R chases you. A yellow star marks your shot.

Press any control to start. Hold a fire key to shoot again after the previous shot clears.
After a hit, release all controls. Press any control to play again.

Hold W and A to move up and left. Add L and semicolon to fire down and right.
Opposite keys cancel on their axis. At a wall, you can still move along it.

## Contract

- Owner request: match the smooth movement of Arena Blaster on the CoCo.
  The current prototype moves in character cells.
- Prototype choice: one room, one robot and one shot at a time.
- Owner request: combine movement and fire keys for independent diagonal directions.
- Owner request: use the two groups of keys from the CoCo game.
- Prototype choice: W, A, S and D move up, left, down and right.
- Prototype choice: O, K, L and semicolon fire up, left, down and right.
- Starter default: NTSC C64 with 64 KiB of RAM, VIC-II 6567 and SID 6581.
- Starter default: VICE x64sc with the ntsc model.
- Starter firmware: KERNAL 901227-03 revision 3, BASIC 901226-01 and character ROM 901225-01.
- Starter loader: VICE starts the PRG. Its BASIC line starts the machine code.

See the [target settings](../../guidance/starter/toolchain.md#target-tables).

## Check the encounter

Run the checks from the repository root:

```sh
uv run python scripts/c64.py check projects/arena-blaster
```

Each check compares the screen cells, their colours, the rendered picture and the border.

| Build | Setup | Expected result |
| --- | --- | --- |
| Main | No controls | The room waits for the first key. |
| Strafe | Hold A and L | The player steps left and shoots down. |
| Hit | Fire right with the robot one cell away | The robot and the shot disappear. The win message appears. |
| Chase | Move right with a robot step due | The player and robot move closer. |
| Caught | Shoot up with the robot one step away | The robot reaches the player. The loss message appears. |
| Edge | Move and shoot left beside the wall | The wall stops the player and absorbs the shot. |
| Northwest, northeast, southwest, southeast | Move diagonally and aim back | The player steps diagonally. The shot travels two cells in the opposite direction. |
| Slide | Move and fire up and left at the left wall | The player slides up. The wall absorbs the shot. |
| Opposed | Hold all eight controls | The player stays still and holds fire. |
| One-axis | Hold W, S, D and O, K, semicolon | The player moves right and shoots up. |
| Replay | Win, hold fire, release, then press A | A fresh encounter starts at the initial positions. |

The check builds supply control bits after the keyboard scan. The main build reads the keyboard.
The [held keys example](../../examples/held-keys/README.md) shows how to test the switches in VICE.
