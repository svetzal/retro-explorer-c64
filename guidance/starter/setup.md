# Manual setup and checks

Use this guide to do the setup yourself or to find the cause of a setup
problem. For a start that an agent leads, use the [README](../../README.md).
Run all commands from the starter folder.

## Bootstrap

For a new project, the agent runs bootstrap with the target of the project:

```sh
sh scripts/bootstrap.sh c64-pal
```

The targets are `c64-pal` and `c64-ntsc`. Bootstrap does these steps:

1. If uv is missing, it installs uv with Homebrew. If Homebrew is missing, it
   uses the [official uv installer](https://docs.astral.sh/uv/getting-started/installation/).
2. It prepares the locked Python environment (`uv sync --locked`).
3. It writes the local reference index, `local/INDEX.md`. It does not
   download or convert references.
4. It installs 64tass and VICE if they are missing.
5. It places the ROMs of the target and compares them with their checksums.
6. It runs the doctor for the target.

If the agent cannot find `uv` after bootstrap, use the uv path that bootstrap
prints. Bootstrap does not change the folders in `projects/`.

Bootstrap installs the tools on Apple Silicon macOS and Ubuntu 24.04 only.
On other hosts, install them manually. Read
[supported hosts](toolchain.md#supported-hosts).

## Tools

64tass and VICE are host programs. They are not in the Python environment.
To find them and check the firmware of a target, run:

```sh
uv run python scripts/doctor.py --target c64-pal
```

To install the missing tools without the other bootstrap steps, run:

```sh
uv run python scripts/native.py
```

On macOS, this installs the Homebrew formulae `vice` and `tass64`. On Ubuntu
24.04, it installs the apt packages `vice` and `64tass`. On Ubuntu, it needs
root or non-interactive sudo. Do not ask the owner for a password. An
administrator must give the account that access, or install the packages.

For a manual installation, use these sources:

- [64tass](https://tass64.sourceforge.net/)
- [VICE](https://vice-emu.sourceforge.io/)

If a tool is not on `PATH`, set its override variable: `TASS64`, `X64SC` or
`C1541`. Read [tool roles](toolchain.md#tool-roles).

## Firmware

To place and check the ROMs of a target without the other steps, run:

```sh
uv run python scripts/setup.py --target c64-pal --firmware-only
```

Setup takes the ROMs from the installed VICE. If they are not there, it
downloads the pinned VICE source release. It writes the ROMs to ignored
`local/roms/C64/`. No ROM goes into Git. If a ROM in that folder is different,
setup stops. Examine the file before you replace it.

`scripts/c64.py` checks the ROMs again before each launch. Do not start VICE
manually to go around a checksum error. Read
[firmware and launching](toolchain.md#firmware-and-launching).

## References

The books are in `resources.json`. Each entry gives its source URL, its
SHA-256 and its redistribution status. To list them, run:

```sh
uv run python scripts/setup.py --list
```

To download one book and convert a range of pages, run:

```sh
uv run python scripts/setup.py --resource c64-prg --pages 395:397
```

Setup compares the download with its SHA-256. Docling converts the pages on
this computer. The first conversion downloads the model weights. Measured on
Apple Silicon: two pages of `c64-prg` took about 20 seconds, with the
download.

To convert all the books, run `uv run python scripts/setup.py` with no
options. A full book is slow. Convert the pages that you need first.

The results are in ignored `local/`:

- `local/INDEX.md`: each book and its converted pages.
- `local/references/<id>/source.pdf`: the downloaded book.
- `local/references/<id>/text.md`: the text, with one `## PDF page N`
  section for each page and a link to the full page image.
- `local/references/<id>/docling-pages/`: the page records and the images.

A later run keeps the converted pages and adds the new range. Read
[reference lookup](references.md) to find and cite a page. Check the OCR
text against the page image, especially for code, tables and diagrams.

A free download does not change the copyright of a book. Downloaded and
converted content stays out of Git.

## Checks of the starter

To run the tests and the style checks of the starter, read
[Python tools](python.md). It gives the commands and the
[complete validation](python.md#complete-starter-validation).
