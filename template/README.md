# Project name

Replace this file with the README of your project. Copy the `template/` folder
to `projects/<name>/` first. Name the folder after the idea of the owner.

The program in this folder prints `HELLO, WORLD!` with the KERNAL. Then it
waits in a main loop that passes the `frame` label once in each frame. Replace
it with your program.

## What the owner asked for

Write the request of the owner here, in plain words.

## How to run it

Commands start in the starter folder:

```sh
uv run python scripts/c64.py run projects/<name>
uv run python scripts/c64.py check projects/<name>
```

The `run` command opens VICE. Close the window to stop it.

## Contract

Write each item before you write hardware-dependent code. Keep `c64.toml`
the same as this list. Mark a starter default as a default, not as a choice of
the owner.

- C64 model and revision: C64, PAL (starter default)
- VICE machine and model: `x64sc`, model `c64` (starter default)
- Video standard: PAL, VIC-II 6569 (starter default)
- RAM: 64 KiB (starter default)
- Sound chip: SID 6581 (starter default)
- Firmware: KERNAL 901227-03 (revision 3), BASIC V2 901226-01 and character
  ROM 901225-01 (starter default)
- Controls: none yet
- Loader: VICE autostarts the PRG file. A BASIC line starts the program
  (starter default). To start the program from a D64 disk image, add
  `--disk` to the `run` command.

## Check

`c64.toml` names the label where the check takes its snapshot, and an address
that must never run.

Add `expected.py` with an independent model of the result when the program draws
or stores something that you can check. Read
[development practice](../guidance/starter/development.md) for the files and
the commands.
