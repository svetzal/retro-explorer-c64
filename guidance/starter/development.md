# Development practice

Read this before you write C64 code for a project or an example.

## Establish the contract

A project is a folder, `projects/<name>/`. The folder holds `main.asm`,
`c64.toml`, `expected.py` and `README.md`.

The README starts with what the owner asked for and how to run it in plain
language. Its contract section records these items:

- The C64 model and revision
- The VICE machine (`x64sc`) and its model setting
- The video standard (PAL or NTSC)
- RAM
- The sound chip model
- Firmware: the KERNAL, BASIC and character ROMs that the starter checks
- Controls
- Loader: how the program starts

Write the contract section before you adapt an example, assemble, or write
hardware-dependent code. Read the file back to make sure that the write
succeeded. Keep `c64.toml` the same as the contract.

Notes that you write after a run describe that run. They do not replace the
contract.

Setup selects a starting target. Setup does not establish that a program
supports that target. Keep unknowns explicit. Do not silently select a faster
CPU, more memory or a different chipset to make a test pass.

The standard targets are `c64-ntsc` and `c64-pal`. The
[target tables](toolchain.md#target-tables) give the machine and firmware of
each target. They also give the table to copy into `c64.toml`.
[Project settings](toolchain.md#project-settings) describe the other settings.

### Owner choices and starter defaults

When the owner names no machine, use `c64-ntsc` and the values of its target
table. Record each value as a starter default in the contract. State the
defaults to the owner. Do not claim that the owner confirmed them.

For each configuration choice, identify which of these it is:

- An owner requirement
- A documented default for the selected target
- An agent-selected prototype choice

Cite the applicable guidance for a default. State agent-selected choices to
the owner without attributing consent.

An animation needs no controls unless the owner asks for them. The defaults
let the first prototype proceed. Explicit requirements and existing project
notes take precedence over defaults. Ask when you must resolve the
configuration of a physical machine or a conflicting requirement.

The firmware comes with VICE. The starter checks each ROM against its
recorded checksum. Read
[firmware and launching](toolchain.md#firmware-and-launching).

## Hardware before code

Read the sources before you write code that depends on the hardware. This
applies to display setup, sound, input, interrupts, memory layout, firmware
calls and instruction timing. Do these two actions first:

- Load [reference lookup](references.md).
- Read the passages that apply to the selected target.

Do not start from remembered tables. Do not wait until the screen looks wrong
to read the source. If you copy setup from a working example, still read its
cited primary passages for the selected target. Downloading or converting a
page does not count as reading it. Reuse facts that you already checked in
this session.

For a display, establish these facts from passages that apply to the selected
hardware:

- The mode's name and meaning in its context. Names in BASIC, in the operating
  system and in the hardware registers can differ. Do not assume that they
  are interchangeable.
- Resolution, available colours, pixel encoding, row stride and the size of
  the display memory. Show how the sizes follow from the layout.
- The registers, field values, memory selection, alignment rules, and shared
  bits that setup must preserve.
- The colour behaviour for the selected video standard and display. Do not
  treat the appearance in an emulator as a source.

Keep a short source note beside the code. In the note, give what you checked,
the citation, and the values that you derived from it.

Read tables and diagrams as images when the bit order or a label is
uncertain. If a source does not cover the selected target, find a source that
does before you continue. A shared chip name or a contents entry does not
establish that two machines behave the same.

Derive expected test values from the sourced layout, independently of the
code that you test. Check boundary pixels, row transitions and the limits of
memory areas.

Then use a small display check in the emulator to inspect the chosen mode and
colours. Do this before you build the full feature. Passing arithmetic tests
cannot show that the hardware mode is correct.

If the result contradicts the source, examine the target, the scope of the
source and the setup code together. Do not cycle through guessed register
values until something looks correct.

## Build and check

Keep deterministic computation separate from display, input and disk I/O. Use
fixed test vectors and compare exact output values where you can.

Use 64tass for assembly and VICE for machine integration. Build, run and check
only through `scripts/c64.py`. CPU-only tests cannot prove display, sound, firmware or
disk behaviour.

Allocate code, data, display memory, buffers and the stack as explicit address
ranges. Check that the ranges do not overlap, and that they stay in the memory
that the target has. Reserve state in a separate region. Do not put state
inside code that grows.

Initialize state before you read it. Preserve shared hardware bits when you
change one part of a register.

Keep evidence separate:

- CPU tests prove arithmetic and memory transformations.
- Emulator tests prove behaviour under the declared machine configuration.
- Visual checks prove that a person inspected the displayed result and the
  interaction.
- Physical-hardware checks establish behaviour on the named real machine.

A process that exits successfully does not prove a successful boot. Check a
meaningful program state. A direct load of a program does not prove that a
disk image works. Report the minimum memory and the loading instructions with
any program that you give to someone.

Assemble the smallest complete increment before you extend it. Do not leave
invented instructions or stubs in a feature that you call finished. If the
build fails, report runtime behaviour as untested.

## Check the feature you claim

Choose checks for the requested feature and the declared target. A first
prototype needs a small complete path through its behaviour, not every
experiment or every target.

Use the methods below when their boundary matters. Report an untested boundary
plainly. Do not expand a narrow pass into a playability claim.

Before you inspect the output of a run, write the expected outcomes from the
contract, the source facts and the intended artwork. Use an alternate route
or sequence where it could show a bug. Use a negative control that breaks the
claimed behaviour, and see the check fail.

Do not repair a failed expectation by copying the observed result. Resolve the
difference against the requirement first.

[The evidence the tools collect](toolchain.md#evidence-the-tools-collect)
lists what `scripts/c64.py check` can capture and compare. If a claim needs evidence
that the tools do not collect, the claim is untested. Say so. Offer a lab to
add the ability.

A capture is not a person who looks at a window, a monitor or a physical
machine. Never report a capture as a visual inspection.

### Input

For an input claim, deliver press, hold and release through the emulated
input device. Then examine the resulting program state. Keep a run without
input as the no-input control. Add a wrong-key control that must fail. Check
release and a second press across the relevant state change.

A test that writes input values into memory after the program reads its
input tests program logic only. Keep that useful test separate from input
delivery. Emulator input does not establish host key delivery, window focus or
physical controls. Claim those only after you check those paths.

### Sound

A counter of sound calls proves that the program called the routine. It does
not prove output, duration or audibility. For a waveform claim, check the
sound hardware state or the emulator's audio output.

State whether a duration is measured or calculated. Give its basis. Derive the
expected pitch or level from the program and the sources, not from a capture.
Add a muted or wrong-routing control that must fail.

Emulator audio output is separate evidence from host playback, listening and
physical output. Keep those limits explicit when any of them is untested.

### Artwork and display

Derive expected pixels from art and scene positions that you specify
independently. Do not derive them from bytes that you read back from the same
emulator memory that you check. That oracle can confirm placement and accept
corrupt art.

Display memory cannot show a wrong display mode or a wrong bit order. For a
claim about the rendered display, compare a captured frame with an
independent expected picture. Include a control that a memory check cannot
catch, such as a wrong mode. Also open the captured image with an image
viewer. Do not make a captured output the new expected picture.

Static captures do not establish animation cadence or tearing. Host
presentation and physical displays are separate checks.

### Test-harness controls for dynamic games

A game with moving opponents, random events or levels changes with each rule
that you adjust. Do not write an input script that plays the game as a person
would. Do not model the whole game so that a script can follow it. That work
takes much time and many tokens, and a small change to a rule breaks it.

Build test-harness controls into the program instead. Each control removes
one dynamic part, so a short input script can reach one game element and check
it. Examples of controls:

- The player does not lose a life when an opponent hits it.
- The opponents do not move, or they move on a fixed path.
- The random-number generator starts from a fixed seed.
- The game starts at level N, or with a fixed layout.
- There is only one opponent, at a fixed position.
- A collision sets a flag but does not end the game.

Obey these rules for controls:

1. Select each control with an assembler symbol that a build variant defines.
   Declare the variants in `c64.toml` as
   [project settings](toolchain.md#project-settings) describe. The main build
   has no controls.
2. Put a comment on each control that says it is only for the check.
3. Use one set of controls to check one element. Write a short script, and in
   `expected.py` model only that element.
4. Keep at least one check of the main build without controls. For example,
   check the first frames of play and the no-input control. Then the checks
   show that no control is active in the game that the owner plays.
5. A pass with a control does not prove the behaviour that the control
   removes. Check that behaviour with its own short script. For example, let
   one opponent hit a player that does not move.
6. List the controls and the checks that use them in the project's README.

## Do not write launchers

Do not write or copy a launcher. A project is a folder that `scripts/c64.py` builds,
launches and checks:

```sh
uv run python scripts/c64.py --help
uv run python scripts/c64.py build projects/<name>
uv run python scripts/c64.py run projects/<name>
uv run python scripts/c64.py snapshot projects/<name>
uv run python scripts/c64.py check projects/<name>
```

The tool checks the firmware that the target names before it starts the
emulator. If the firmware check fails, run the recovery command that the tool
prints. Read [firmware and launching](toolchain.md#firmware-and-launching).

Start a project with a copy of [`template/`](../../template/README.md). Do not
copy an example folder as the base of a project. Each example shows one
practice.

`expected.py` is the independent model of the result. Write it from sourced
facts and requirements, never from the assembled bytes or a captured snapshot.
`expected.py` and `scripts/c64.py check` are the test of a project. Do not write a
spec that tests `expected.py` or `scripts/c64.py`. If the check could pass a wrong
result, break the program once in a copy and see the check fail.

## Learn from evidence

State a testable question before an experiment. Record the command, target,
result and conclusion. Distinguish measured facts, sourced facts, proposals
and uncertainty. Update current-state notes in place. Git keeps their history.

A citation does not make a transcription correct. Compare each register write
with the cited row. If a second source corrects a fact, update the code and
the source note together. Do not keep the earlier transcription in a stub.
