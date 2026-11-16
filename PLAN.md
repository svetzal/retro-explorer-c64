# Active plan

Keep this file limited to open work. Remove each item when its acceptance
criteria are met. Keep its evidence in the relevant guide or example. Nobody
is working on these items now unless the item says so.

## Continue from here

Read [AGENTS.md](AGENTS.md), then choose one open item below. Use the
[guidance map](guidance/README.md) for the current guides. Preserve the
ignored `local/` and `build/` folders and the prepared `.venv`.

## Open work

- **The emulator choice.** VICE (`x64sc`) is the emulator for now. The choice
  stays open until experience with this starter confirms it or shows a
  better one. Record the controls and measurements that VICE gives in
  [the evidence the tools collect](guidance/starter/toolchain.md#evidence-the-tools-collect),
  each with a check that has a failure control.
- **The C64 Ultimate as a physical target.** Stacey owns a C64 Ultimate. She
  describes an API in its FPGA that can write and read memory, capture the
  screen and reboot the machine. That API could let the agent run and measure
  a program on physical hardware. Nobody has integrated or checked it in this
  starter. An integration belongs under `scripts/`, as
  [the rules for scripts](scripts/AGENTS.md) describe. Each result must name
  the device. A result from it does not establish behaviour on every C64.
- **Technique guides.** There are none yet. The first guides come from labs
  and BUILD work, as the [technique index](guidance/techniques/README.md)
  describes. Do not write guides ahead of a concrete need.
- **Examples beyond a first screen.** A first example sets up a screen. Each
  later example comes from a lab or a project that needs it. Obey
  [the rules for examples](examples/AGENTS.md).
- **Reference collection.** Choose the first sources in `resources.json`.
  Check the conversion quality of the difficult pages, such as register
  tables and assembly listings.
- **Host onboarding.** No check establishes the first run on a clean host.
  Linux host onboarding is not checked. Record the result for each host in
  [supported hosts](guidance/starter/toolchain.md#supported-hosts).
- **The `c64-ntsc` target.** Its timing needs its own checks. A result on
  `c64-pal` does not establish `c64-ntsc` behaviour.
