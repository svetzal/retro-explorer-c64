# Scripts

The scripts build, start, record and measure. Run each command from the
starter folder. To change a script, read [the rules for scripts](AGENTS.md).

## Commands

| Command | What it does |
| --- | --- |
| `sh scripts/bootstrap.sh <target>` | Prepares Python, 64tass, VICE, the ROMs of the target and the reference index. Then it runs the doctor. |
| `uv run python scripts/doctor.py --target <target>` | Finds the tools and compares the ROMs of the target with their checksums. It does not start VICE. |
| `uv run python scripts/native.py` | Installs the missing tools with Homebrew or apt. |
| `uv run python scripts/setup.py --target <target> --firmware-only` | Places the ROMs of the target in `local/roms/C64/` and checks them. |
| `uv run python scripts/setup.py --guidance-only` | Writes `local/INDEX.md`. It does not download anything. |
| `uv run python scripts/setup.py --list` | Lists the references in `resources.json`. |
| `uv run python scripts/setup.py --resource ID` | Caches one source. |
| `uv run python scripts/setup.py` | Downloads and converts all the references. This is slow. |
| `uv run python scripts/c64.py build <folder>` | Assembles the project. Add `--variant <name>` for a variant and `--disk` for a D64. |
| `uv run python scripts/c64.py run <folder>` | Assembles, checks the ROMs and opens VICE for a person. Add `--target`, `--variant` or `--disk`. |
| `uv run python scripts/c64.py snapshot <folder>` | Runs to the checkpoint and saves the evidence. Add `--target`, `--variant` or `--audio`. |
| `uv run python scripts/c64.py check <folder>` | Runs each target and variant to the checkpoint and compares the evidence with `expected.py`. Add `--target` or `--audio`. |

The targets are `c64-ntsc` (the default) and `c64-pal`. `c64.py` returns one of these
exit statuses:

- 0: the command is complete and all results pass.
- 1: a result fails, or the tool cannot use the project, the tools or the
  ROMs. The message tells the cause.
- 2: the command line is wrong.

## Modules

| File | Contents |
| --- | --- |
| `bootstrap.sh` | The first command on a new host. |
| `doctor.py` | The health check of the tools and the firmware. |
| `native.py` | Finds and installs 64tass and VICE. |
| `firmware.py` | Places and checks the ROMs in `firmware.json`. |
| `setup.py`, `references.py` | Cache references and convert PDF pages. |
| `c64.py` | The project tool: settings, build, launch and the comparison with `expected.py`. |
| `vice_session.py` | Starts `x64sc`, runs the program to the checkpoint and collects the evidence. |
| `vice_monitor.py` | The client for the VICE binary monitor protocol. |

Each module has its spec beside it, for example `c64_spec.py`. The negative
controls of the examples are in `c64_spec.py`. The specs marked
`integration` use the real Docling, 64tass and VICE. They skip when a tool or
the ROMs are missing.

Use `--pages A:B` to convert a range of PDF pages. Repeat `--resource` to
select more sources. See the [reference guide](../guidance/starter/references.md).

## Measured limits

These limits are measured with VICE 3.10 and 64tass 1.60.3243 on Apple
Silicon macOS. The [toolchain guide](../guidance/starter/toolchain.md#evidence-the-tools-collect)
gives the full table of abilities.

- Keyboard input goes into the KERNAL keyboard buffer, once, at one label. A
  program that reads the keyboard matrix does not see it.
- There is no joystick input.
- The rendered frame is VICE's frame buffer. It is not a window, a monitor
  or a television. No person looks at it.
- `check` does not use the disk image. A test shows that VICE starts the
  template from its D64. It does not show which drive emulation VICE used.
- The tool corrects two VICE 3.10 display defects: the 4 pixels that VICE
  does not send, and the PAL window row. Read the
  [toolchain guide](../guidance/starter/toolchain.md#vice-behaviour-that-the-tools-correct).
- Boot and autostart need about 3 million emulated cycles. The
  `cycle_limit` must include them.
- A check of the first-screen example on both targets, with both variants,
  takes about 5 seconds.
- Docling converted two pages of `c64-prg` in about 20 seconds, with the
  download.
