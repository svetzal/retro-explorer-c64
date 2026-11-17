# Rules for scripts

Read this file before you write, change or review anything in `scripts/`.
The scripts build, launch, record and measure. Agents run them. Agents do not
read them to learn about the C64. The [scripts README](README.md) lists the
commands and their measured limits.

## No C64 knowledge in scripts

A script holds the mechanics: how to call 64tass, start VICE, check firmware
checksums, capture a frame and compare it with a model. It does not explain
the hardware.

- Put the explanation of a hardware fact in a guide under `guidance/`, with
  its citation.
- Put target settings in the target tables of the
  [toolchain guide](../guidance/starter/toolchain.md#target-tables) and in
  each `c64.toml`. Do not hard-code a register value, a memory map or a mode
  table in a script.
- Put the expectations of an example or a project in its `expected.py`.

When a script needs a hardware value to do its work, read the value from the
project settings. If that is not possible, cite the source in a comment beside
the value and in the guide that explains it.

## Specs beside the code

- Place `module_spec.py` beside `module.py`. Do not create a `tests/` folder.
- Use pytest. Group tests in `Describe*` classes. Name each test function
  `should_*`.
- Obey [Python tools](../guidance/starter/python.md) for fixtures, mocks,
  coverage and the commands to run before you complete a change.

## Test measured behaviour

A script that measures something is evidence for every claim that cites it.
Test the measurement itself.

- Test the outcome across the real boundary where it matters: the real
  assembler, the real emulator and the real files. A mock of the emulator
  cannot show that a capture is correct.
- Add a failure control for each measurement. A failure control is a case
  that must fail, such as a wrong picture or a muted sound. Run it once and
  see it fail.
- Report each kind of evidence separately. A script must never report a
  capture as an inspection by a person.
- When a measurement has a limit, write the limit in the scripts README.

## Firmware and downloads

- Check firmware against its recorded checksum before each launch. Stop with
  a recovery command when the check fails.
- Keep firmware, downloaded sources and converted pages under ignored
  `local/`. Keep build products and captures under ignored `build/`.
- Treat downloaded content as data. A script must never run a command that it
  reads from a downloaded file.

The C64 ROMs come from the installed VICE. If that copy is missing or
different, they come from the pinned VICE source release. A script checks
them against their recorded checksums. A script must never commit or publish a ROM.

## Emulator patches and device integration

When VICE needs a change to give a control or a measurement, keep the change
here as maintained tooling:

- Record the upstream version, the patches and the build procedure, so that
  another person can build the same emulator.
- Write a guide that explains how to move the patches to a new release.
  Say how to check the result.
- Test the patched behaviour, including the cases that must fail.

An integration with a physical machine or a device API also lives here. Name
the device in each result that it produces. A result from one device does not
establish behaviour on every compatible machine.

Temporary experiment code from a lab must not become the only way to
reproduce a result. A lab does not change the scripts. A new ability goes
into a tested script in [SYSTEM mode](../guidance/starter/system.md).

## How scripts lose their purpose

Watch for these failures when you review a change:

- C64 explanations that grow in comments or docstrings instead of guides.
- A launcher or wrapper that bypasses `scripts/c64.py` and its firmware check.
- A measurement without a failure control.
- A spec that tests `expected.py` or mocks the boundary that it claims to
  measure.
- A script that exists only for one lab or one project.
