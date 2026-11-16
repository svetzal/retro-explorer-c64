# C64 development toolchain

Load this file before you assemble, build a disk image or start the emulator.
First read the contract in `projects/<name>/README.md`. Do not take the RAM,
the video standard, the sound chip or the firmware from what is installed.

## Tool roles

| Tool | Executable | Override | Purpose |
| --- | --- | --- | --- |
| 64tass | `64tass` | `TASS64` | 6502 assembly. It writes a PRG, a VICE label file and a listing. |
| VICE | `x64sc` | `X64SC` | Cycle-exact C64 emulation, with the binary monitor for evidence. |
| VICE | `c1541` | `C1541` | D64 disk images. |

These are host executables. They are not in the uv Python environment. To
find them, run this command:

```sh
uv run python scripts/doctor.py --target c64-ntsc
```

The doctor finds each tool and compares each ROM of the target with its
checksum. It does not start VICE. Without `--target`, it says that it did not
check the firmware. It returns nonzero when a tool is missing or a ROM is
wrong.

To use a specific executable, set its override variable to the path. The
tools look for an executable in this order:

1. The override variable.
2. `PATH`.
3. `/opt/homebrew/bin`, on Apple Silicon macOS only.

`scripts/c64.py` uses the same order. Do not copy a private path of a
developer into a default.

`scripts/c64.py` calls 64tass with these options: `--cbm-prg`, `--ascii`,
`--vice-labels`, a label file, a listing and one `-D` for each define of the
variant. The `--ascii` option makes 64tass read the source as Unicode. Then
`.text` converts the text to PETSCII. After `.enc "screen"`, it converts the
text to screen codes. The 64tass manual gives the two tables: "The none
encoding for Unicode" and "The screen encoding for Unicode".

## Supported hosts

`sh scripts/bootstrap.sh <target>` supports two hosts:

- Apple Silicon macOS (arm64). Bootstrap uses Homebrew. It installs the
  `vice` and `tass64` formulae.
- Ubuntu 24.04. Bootstrap uses apt. It installs the `vice` and `64tass`
  packages. It needs root or an account with non-interactive sudo.

Bootstrap stops on an Intel Mac before it installs anything. It stops on
other Linux distributions with a message. On those hosts, install the tools
manually. Read [manual setup](setup.md).

Measured on Apple Silicon macOS 27.2 with VICE 3.10 and 64tass 1.60.3243:
bootstrap, the doctor and the full suite pass. A check of the first-screen
example on both targets takes about 5 seconds.

The Ubuntu path is not verified. These are the known risks:

- The Ubuntu `vice` package can be without the C64 ROMs. Then setup takes
  the ROMs from the pinned VICE source release. Read
  [firmware and launching](#firmware-and-launching).
- `x64sc` opens a window, also for a check. A host without a display can need
  a virtual display, for example `xvfb-run`. No check covers this.
- The Ubuntu package can have a different VICE version. The tools use
  binary monitor commands that need VICE 3.6 or later (VICE manual, sections
  13.4.22 and 13.4.24). Only VICE 3.10 is measured.

## Firmware and launching

The firmware is the KERNAL, BASIC and character ROMs that VICE supplies.
`firmware.json` records the file name, size and SHA-256 checksum of each ROM.
It also records the ROMs of each target.

| File | ROM | Commodore part | Size |
| --- | --- | --- | --- |
| `kernal-901227-03.bin` | KERNAL, revision 3 | 901227-03 | 8192 bytes |
| `basic-901226-01.bin` | BASIC V2 | 901226-01 | 8192 bytes |
| `chargen-901225-01.bin` | Character generator | 901225-01 | 4096 bytes |

Bootstrap places the ROMs. For an existing checkout, use this command:

```sh
uv run python scripts/setup.py --target c64-ntsc --firmware-only
```

Setup puts each ROM in `local/roms/C64/` from one of these sources:

1. A copy that is already there. If it is different, setup stops. Examine the
   file before you replace it.
2. The installed VICE: `<prefix>/share/vice/C64/` beside the `x64sc`
   executable.
3. The VICE 3.10 source release, pinned by its SHA-256 in `firmware.json`.
   Setup keeps the download in `local/firmware-sources/`.

Setup compares each ROM with its checksum before it writes any ROM.

Before each launch, `scripts/c64.py` compares the target's ROM files with
`firmware.json`. If a ROM is missing or different, it stops and gives the
recovery command. Do not start VICE until the check passes.

VICE loads the ROMs from `local/roms/`. The tool gives
`-directory "<starter>/local/roms:$$"` to `x64sc`. VICE looks for a machine's
files in the `C64` folder of each search folder (VICE source `src/sysfile.c`).
The tool does not use `-kernal`, because `-model` replaces the KERNAL that
`-kernal` selects. This was measured with VICE 3.10. During a check, the tool
also reads the ROM bytes from the running emulator and compares them with
`firmware.json`.

`run` opens VICE at normal speed for a person:

```sh
uv run python scripts/c64.py run projects/<name>
```

`snapshot` and `check` start VICE with a minimized window and no sound, and
control it through the binary monitor. They use these `x64sc` options:

| Option | Reason |
| --- | --- |
| `-default` | Ignore the settings file of the person. |
| `-model <model>` | The machine of the target. |
| `-sidmodel <0 or 1>` | The SID of the target: 0 is the 6581, 1 is the 8580. |
| `-binarymonitor` and `-binarymonitoraddress ip4://127.0.0.1:<port>` | The monitor connection, on the local host only. |
| `-autostart-warp` | Fast boot and load. VICE stops warp mode when autostart is complete (`src/autostart.c`). |
| `-autostartprgmode 1` | Put the PRG directly into memory ("Inject"), not through a virtual drive or a disk image. |
| `-limitcycles <n>` | VICE stops with an error after n emulated cycles. |
| `-minimized` | No window in front of the person. |

The tool does not use `-warp`. In warp mode, VICE skips rendered frames
(`vsync_should_skip_frame` in `src/vsync.c`). Then the captured frame can be
older than the memory.

## Target tables

The standard targets are `c64-ntsc` (the default) and `c64-pal`. Copy the
table of the target into `c64.toml`. Record its values in the contract of the
project README.

| Item | `c64-ntsc` | `c64-pal` |
| --- | --- | --- |
| Machine | C64, NTSC | C64, PAL |
| VICE machine and model | `x64sc`, `ntsc` | `x64sc`, `c64` |
| Video standard | NTSC, 263 lines | PAL, 312 lines |
| VIC-II | 6567 | 6569 |
| SID | 6581 | 6581 |
| RAM | 64 KiB | 64 KiB |
| KERNAL | 901227-03, revision 3 | 901227-03, revision 3 |
| BASIC | 901226-01, BASIC V2 | 901226-01, BASIC V2 |
| Character ROM | 901225-01 | 901225-01 |

The VICE models `c64` and `ntsc` both use KERNAL revision 3 and the 6581 SID
(`src/c64/c64model.c`). The line counts are from `src/c64/c64.h`.

```toml
[targets.c64-ntsc]
model = "ntsc"                    # VICE -model: C64 NTSC
video = "ntsc"
vicii = "6567"
sid = "6581"
ram_kib = 64
kernal = "kernal-901227-03.bin"
basic = "basic-901226-01.bin"
chargen = "chargen-901225-01.bin"
```

```toml
[targets.c64-pal]
model = "c64"                     # VICE -model: C64 PAL
video = "pal"
vicii = "6569"
sid = "6581"
ram_kib = 64
kernal = "kernal-901227-03.bin"
basic = "basic-901226-01.bin"
chargen = "chargen-901225-01.bin"
```

The sound chip is part of the contract. To use the 8580 SID, set
`sid = "8580"` and record it in the contract. A check of the template with
`sid = "8580"` passed: VICE reported the 8580. No example uses the 8580.

The C64 Ultimate is a possible future target. The starter does not support
it, and no check covers it.

## Project settings

A project folder holds `main.asm`, `c64.toml`, `README.md` and, when it
draws or stores something to check, `expected.py`. `c64.toml` has these
tables:

| Setting | Meaning |
| --- | --- |
| `source` | The assembly file. The default is `main.asm`. |
| `[targets.<name>]` | One target. Copy it from [the target tables](#target-tables). The first target is the default. |
| `[variants.<name>]` `defines` | Assembler defines for one build variant, for example `["MIXED_CASE:=true"]`. |
| `[variants.<name>]` `targets` | Optional. The targets where the variant applies. All targets when absent. |
| `[check]` `checkpoint` | The label or address where the snapshot is taken. |
| `[check]` `hit` | How many times the checkpoint must run before the snapshot. The default is 1. |
| `[check]` `unreachable` | Labels or addresses that must never run, for example `["frame+1"]`. |
| `[check]` `cycle_limit` | The maximum emulated cycles from power-on. |
| `[check]` `screen` | The address where `expected_screen` is compared. |
| `[check]` `colours` | The address where `expected_colours` is compared. |
| `[check]` `border_ring` | How many border pixels around the display window to compare with `expected_border`. |
| `[check.input]` `at`, `text` | Type `text` into the keyboard buffer when the program reaches `at`. Capital letters, digits and spaces only. |

An address is a label, `label+N`, `label-N` or `$hex`. The tool reads the
labels from the VICE label file that 64tass writes.

A variant define sets an assembler symbol. Write `NAME :?= false` in the
source. The variant then sets it with `-D NAME:=true`. Use a variant for a
variation of an example, or for a test-harness control of a project.

Boot, autostart and three frames need about 3 to 4 million cycles. Give the
`cycle_limit` a margin. When the limit stops VICE first, the execution result
fails.

Put the checkpoint in the main loop, after the screen is drawn. VICE gives
the frame that it rendered last. Thus, with `hit = 3`, the captured frame
shows two complete frames of the program.

`expected.py` can have these functions. The tool calls only the functions
that exist. It gives `target=` and `variant=` to a function that declares
them.

| Function | Compared with |
| --- | --- |
| `expected_screen()` | Bytes at `[check] screen`. |
| `expected_colours()` | The low 4 bits of the bytes at `[check] colours`. |
| `verify_state(state)` | `state.ram` (64 KiB), `state.io` (`$D000-$DFFF`), `state.registers` and `state.symbols`. Use `assert`. |
| `expected_frame(chargen)` | The rendered display window as colour codes, 320 x 200. `chargen` is the character ROM read from the emulator. |
| `expected_border()` | The colour code of the border ring. |
| `verify_sound(sound)` | `sound.rate`, `sound.samples` and `sound.writes` (cycle, SID register number from 0, value). Needs `--audio`. Use `assert`. |

## Evidence the tools collect

`check` runs every target and every variant that applies. It writes the
evidence of each run in `build/<folder>/<variant>/<target>/`:

| File | Contents |
| --- | --- |
| `results.json` | Each kind of evidence, its status and its detail. The program SHA-256 and the VICE version. |
| `ram.bin` | The 64 KiB of RAM at the checkpoint. |
| `io.bin` | The I/O area `$D000-$DFFF` at the checkpoint. |
| `registers.json` | The CPU registers at the checkpoint. |
| `frame.png` | The whole rendered frame, with the border, in the VICE palette. |
| `sound.wav`, `sid-writes.txt` | With `--audio`: the SID output and the SID register writes. |
| `vice.log` | The output of VICE. |

The build folder `build/<folder>/<variant>/` also holds the PRG, the label
file and the listing.

Each kind of evidence has its own result:

| Kind | What passes | What it does not prove |
| --- | --- | --- |
| execution | The checkpoint ran `hit` times, VICE stopped with the PC at the checkpoint, and no `unreachable` address ran. | Behaviour after the snapshot. |
| firmware | The KERNAL, BASIC and character ROM bytes in the running emulator agree with `firmware.json`. | Other ROM revisions. |
| machine | VICE reports the video standard, VIC-II and SID of the target. | Physical chips. |
| screen memory, colour memory, state | The bytes and registers agree with `expected.py`. | The picture: a wrong mode or character set shows the same bytes differently. |
| rendered frame | The display window and the border ring in VICE's frame buffer agree with `expected.py`, pixel for pixel, as colour codes. | A window, a monitor or a television. |
| sound | With `--audio`, `verify_sound` accepts the WAV and the SID writes. | What a person hears. |
| visual inspection | Always `not done`. Use `run` and ask a person. | |
| physical hardware | Always `not tested`. | |

A pass with no `expected.py` proves only execution, firmware and machine.

### Abilities

Each ability below is measured by a test in `scripts/c64_spec.py` with the
real 64tass and VICE. Each test has a failure control.

| Ability | Supplied | Measurement | Failure control |
| --- | --- | --- | --- |
| Execution checkpoints, cycle limit | Yes | The first-screen check. | A program that stalls. A program that runs an `unreachable` label. |
| Firmware bytes in the emulator | Yes | The first-screen check. | A changed ROM file stops the launch. |
| Machine resources | Yes | The first-screen check. | A PAL target that names the 6567. |
| Screen, colour and register memory | Yes | The first-screen check. | A wrong letter. A wrong text colour. A wrong border colour. |
| Rendered frame | Yes | The first-screen check. | The lower-case character set, with the same memory. |
| SID output and register writes | Yes, with `--audio` | A tone at volume 15. | The same tone at volume 0. |
| Keyboard input | Yes, through the KERNAL keyboard buffer | `GETIN` reads `GO`. | No input: the checkpoint is not reached. |
| D64 disk image | Yes | `c1541` lists the program. VICE starts the template from the disk. | An empty disk: the checkpoint is not reached. |
| Joystick | No | | |
| Keys in the keyboard matrix | No | | |
| Inspection by a person | No | | |
| Physical C64 or C64 Ultimate | No | | |

Limits of the supplied abilities:

- Keyboard input goes into the KERNAL keyboard buffer (binary monitor command
  "Keyboard feed"). A program that reads the CIA keyboard matrix does not see
  it.
- The disk test does not show whether VICE loaded the program through an
  emulated 1541 drive or through its virtual drive.
- The tool feeds input once, at one label. It does not script a sequence of
  inputs over time.

The VICE binary monitor has a "Joyport set" command (VICE manual, section
13.4.25). The tools do not use it, and no test measures it.

### VICE behaviour that the tools correct

- Display get: VICE 3.10 counts the response length without the 4-byte
  buffer length field. Thus it does not send the last 4 pixels of the buffer
  (`monitor_binary_process_display_get` in `src/monitor/monitor_binary.c`).
  These pixels are in the bottom-right corner, outside the visible area. The
  tool sets them to 0 and records how many are missing.
- PAL display window: on PAL, VICE reports the display window at row 51 of
  the buffer, but the buffer holds it at row 50. The tool moves the window up
  one row. On NTSC, the reported row is correct. This was measured with VICE
  3.10. The PAL border fills buffer rows 15 to 286 for VICE's visible lines
  16 to 287 (`src/viciisc/vicii-timing.h`).
- Cycle limit: when `-limitcycles` stops VICE, the monitor connection closes.
  The tool reports that the cycle limit ended the run.

### Sources

- VICE manual, chapter 13, "Binary monitor",
  <https://vice-emu.sourceforge.io/vice_13.html>, read for VICE 3.10: the
  message layouts and the commands.
- `x64sc -help` of VICE 3.10: the command-line options.
- VICE 3.10 source release, `vice-3.10.tar.gz` (SHA-256 in `firmware.json`):
  `src/sysfile.c`, `src/autostart.c`, `src/vsync.c`,
  `src/monitor/monitor_binary.c`, `src/viciisc/vicii-timing.h`,
  `src/c64/c64model.c`, `src/c64/c64.h`, `src/machine.h`, `src/vicii.h` and
  `src/sid/sid.h`.
- 64tass manual, <https://tass64.sourceforge.net/>: the command-line options,
  the BASIC loader and the text encodings.
- Commodore, *Commodore 64 Programmer's Reference Guide* (1982),
  resources.json id `c64-prg`:
  - PDF 120: the I/O area starts at `$D000`. Colour memory is 4 bits wide.
  - PDF 281: the ROM addresses.
