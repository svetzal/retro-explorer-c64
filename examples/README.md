# Examples

Each example shows one practice on the C64. Examples are how to set up a
screen, read the controls or play sound while a game draws. An agent reads an example
to decide what to do in a project.

An example can have code that builds up a context, and that context is not
part of the example. After the context comes the marked code of the one
practice that the example is about.

An example is not always the best way. It shows one technique, and a starting
point when you do not know what else to do. Treat the examples as building
blocks to study, not as code to copy as it is.

## Run one

Open a terminal in the starter folder. Run an example with this command,
then close the emulator window to stop it:

```sh
uv run python scripts/c64.py run examples/<name>
```

Each example README gives the commands for that example.

## Catalogue

| Task | Example | Targets | Scope |
| --- | --- | --- | --- |
| Put text on the screen | [First screen](first-screen/README.md) | C64 PAL, C64 NTSC | Border and background colours, character set 1 or 2, screen and colour memory. Rendered check of both character sets. |
| Read held keys | [Keyboard scan](held-keys/README.md) | C64 NTSC | Independent movement and fire keys. Manual combination test and automated idle display check. |
| Move three sprites over a fixed arena | [Sprite motion](sprite-motion/README.md) | C64 NTSC | Diagonal pixel movement, a ninth-bit crossing and a timing check. |
| Draw eight overlapping grunts | [Crowd rendering](crowd-rendering/README.md) | C64 NTSC | Character graphics with sprite actors, overlap checks and update timing. |

A result on one emulator configuration does not establish another model or
physical hardware. Each example names its own targets and the procedure that
reproduces its result. Read the [technique guides](../guidance/techniques/README.md)
to understand the design and its sources before you adapt a program.

## Checks

`scripts/c64.py` builds, runs and checks every example. Run it with `--help` to see
its commands. The `expected.py` model and `scripts/c64.py check` are the test of an
example. The root pytest suite runs the real check of each example and its
negative controls.

To write or change an example, read [the rules for examples](AGENTS.md).
