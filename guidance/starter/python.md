# Python support tools

Load this file when you write host-side scripts, asset converters, reference
models or tests. Run commands from the repository root.

## Environment

Use `uv sync --locked` to create `.venv` from `uv.lock`. Use `uv run` for
scripts and checks. Do not install into the system Python. Do not keep a
second requirements file.

Declare a dependency with `uv add`. Commit `pyproject.toml` and `uv.lock`
together. `.python-version` selects the Python version.

Native C64 tools, such as 64tass and VICE, are separate from Python. The
[toolchain guide](toolchain.md#tool-roles) describes them.

## Python conventions

Use typed public functions. Keep pure transformations separate from file and
process I/O. Test packed bytes and numeric outputs, not only rendered
previews. Use `pathlib`, `struct`, `wave` and `subprocess` from the standard
library where they fit. Put generated assets in `build/`.

Put each third-party call behind a small, named gateway when tests need a
controlled boundary. Mock only those gateways, with `Mock(spec=GatewayClass)`.
Keep real tests of the filesystem, executable discovery and the emulator where
their behaviour matters.

## Specs

Place `module_spec.py` beside `module.py`. Do not create a separate `tests/`
folder. Pytest collects `Describe*` classes and `should_*` functions from the
`*_spec.py` files under `scripts/`.

Use fixtures in the nearest `conftest.py`, plain assertions and parametrized
cases. Do not use `unittest.TestCase`, importlib loading, or imports from
another spec. Separate setup, action and assertions with blank lines.

Test outcomes, not private methods, call order or elapsed time. Test
interrupted work and its later resumption together.

Examples and projects have no specs. Their test is `expected.py` and
`scripts/c64.py check`. The spec beside `scripts/c64.py` runs the real check of each example
and its negative controls.

## Before you complete a change

Run these commands:

```sh
uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
```

Combined statement and branch coverage must reach 90%. The threshold does not
replace a check of the behaviour that you changed. Ruff limits the complexity
of each function to 10. Keep larger workflows readable: separate validation,
decisions and external operations.

Keep test evidence that must stay after a rerun under ignored `local/` or
`build/`. Do not keep it in a pytest temporary folder.

## Complete starter validation

Setup for one target prepares that target only. The full suite also runs
emulator checks on the other standard targets. Prepare each standard target
before you run the full suite:

```sh
sh scripts/bootstrap.sh c64-pal
sh scripts/bootstrap.sh c64-ntsc
```

Then run the health check for each target and the full suite:

```sh
uv run python scripts/doctor.py --target c64-pal &&
uv run python scripts/doctor.py --target c64-ntsc &&
uv run pytest --cov -ra
```

Inspect the exit status, the coverage result and the skip reasons. A pass
with skipped emulator integrations is not a complete validation.

## Dependency checks

Audit the lockfile, including optional groups:

```sh
uv export --all-groups --format requirements-txt --no-emit-project \
  | uvx pip-audit -r /dev/stdin --disable-pip
uv pip list --outdated
```

Do not audit only the temporary environment that contains pip-audit.

For C64 binaries and emulator checks, load [toolchain.md](toolchain.md). For
books and OCR, load [references.md](references.md).
