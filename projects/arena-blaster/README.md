# Arena Blaster

Open lab: projectile-rendering

Build a Robotron-style game with WASD for movement and O, K, L and semicolon for fire.
Use the [keyboard scan](../../guidance/techniques/held-keys.md) to read movement and fire independently.

## Run

From the repository root, run:

```sh
uv run python scripts/c64.py run projects/arena-blaster
```

Press a fire key to start. The level banner stays up for two seconds.
You are the yellow and red figure. Four green grunts chase you.
Hold a fire key for repeated shots. A grunt gives 10 points.

You start with three lives. Contact freezes play for 1.5 seconds before you lose a life.
Clear the opening wave to enter level 2 with your score and remaining lives.
Eight grunts chase you in level 2. Clear it, then press fire to play again.

Hold W and A to move up and left. Add L and semicolon to fire down and right.
Opposite keys cancel on their axis. At a wall, you can still move along it.

## Contract

- Owner request: match the smooth movement of Arena Blaster on the CoCo.
  The opening wave uses the CoCo level rules.
- Graphics choice: keep the room in character mode.
  Use [hardware sprites](../../guidance/techniques/sprite-motion.md) for the player, shots and first-wave grunts.
  The second wave uses [character graphics](../../guidance/techniques/crowd-rendering.md) for eight grunts.
- Prototype choice: four grunts and three shot slots in the opening room.
- Owner request: combine movement and fire keys for independent diagonal directions.
- Owner request: use the two groups of keys from the CoCo game.
- Prototype choice: W, A, S and D move up, left, down and right.
- Prototype choice: O, K, L and semicolon fire up, left, down and right.
- Starter default: NTSC C64 with 64 KiB of RAM, VIC-II 6567 and SID 6581.
- Starter default: VICE x64sc with the ntsc model.
- Starter firmware: KERNAL 901227-03 revision 3, BASIC 901226-01 and character ROM 901225-01.
- Starter loader: VICE starts the PRG. Its BASIC line starts the machine code.

See the [target settings](../../guidance/starter/toolchain.md#target-tables).

## CoCo progression

The CoCo project's README, assembly, sprite art and check fixtures define the reference game.
The C64 opening wave uses fixed starting positions. Actors update once per two NTSC fields.

Each grunt chases on alternate updates. The six-digit score awards another life at each 1000 points.
Three hardware slots hold player shots. The CoCo uses up to ten.

| Reference milestone | C64 status |
| --- | --- |
| Level 1 teaches shooting with four grunts | Playable with sprites, diagonal controls, score, lives and respawn |
| Level 2 teaches diagonals with eight grunts | Playable with eight pursuing grunts, shots, collisions and respawn |
| Level 3 adds fast hunters | Pending |
| Level 4 adds gifts after each sixth shot kill | Points, double, spread and star shots pending |
| Level 5 adds shooters | Enemy bullets and shooter rotation pending |
| Level 6 adds bombs | Area damage and bullet clearing pending |
| Level 8 adds jinxes | Slow fire, heavy movement and hunter blitz pending |
| Later levels start with up to 20 enemies | Crowd rendering and timing need a trial |
| Title and game over | Fire starts play. The ten-entry high-score table, initials, sound and attract sequence are pending. |

Double, spread and star last ten seconds in the reference. Slow and heavy last five seconds.
The reference keeps gifts and jinxes between levels. Death clears both.
Grunts give 10 points, shooters give 30 and hunters give 50.
The reference stores the high-score table in RAM until power-off.

## Check the two waves

Run from the repository root:

```sh
uv run python scripts/c64.py check projects/arena-blaster
```

The main build checks the title. The start build checks the teaching banner and the four starting positions.
Movement checks use fixed control bits for all four diagonals, opposing keys and wall contact.
Collision checks place one grunt near the player or shot.

The bonus check starts at 990 points. The clear check starts with the final grunt and two lives.
The respawn and game-over checks shorten the death pause to one update.
Each check compares the screen, colours, border and rendered actors in NTSC VICE.

The crowd checks cover diagonal movement and fire, a death in level 2 and a hit on the eighth grunt.
The timing check measures eight game updates while the eight grunts pursue and the player fires repeatedly.
At the last checkpoint, three shots are in flight.

See the [sprite guide](../../guidance/techniques/sprite-motion.md) for the graphics sources.
See the [keyboard example](../../examples/held-keys/README.md) for a manual key test.
