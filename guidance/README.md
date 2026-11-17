# Agent guidance

This folder holds what an agent reads to work well in this starter. Beginners
do not need it. They start with the [README](../README.md). Agents enter
through [AGENTS.md](../AGENTS.md), which says when to read each part.
[PLAN.md](../PLAN.md) holds open work. [AGENTS.md](AGENTS.md) in this folder
gives the rules for writing guidance.

| Folder | Holds | Read it when |
| --- | --- | --- |
| [starter/](#use-the-starter) | How to use this repository: setup, tools, references and the BUILD, LAB and SYSTEM procedures | You set up, build, test, look up a source or work in a lab |
| [techniques/](techniques/README.md) | C64 knowledge, organized by the effect that the owner wants | You choose or apply a technique for the owner's project |

Read the guide for the task at hand. Each technique guide cites its sources
and lists its open questions. Open the cited pages when a claim matters to the
work.

## Use the starter

- [Set up manually or recover a first run](starter/setup.md).
- [Build programs and launch with verified firmware](starter/toolchain.md).
- [Establish a target and check C64 behaviour](starter/development.md).
- [Work on host scripts and prepare the full suite](starter/python.md).
- [Find source pages and cite evidence](starter/references.md).
- [Work in a lab: answer a technical question, then codify it](starter/lab.md).
- [Change the starter itself in SYSTEM mode](starter/system.md).

## Techniques

Start with the [technique index](techniques/README.md). It maps the effect
that the owner wants to a guide, and states the current evidence for each.

## Kinds of evidence

The checks for each example are in the
[example READMEs](../examples/README.md). The supported hosts are in
[the toolchain guide](starter/toolchain.md#supported-hosts).

Keep these kinds of evidence distinct:

- assembly
- emulator state
- rendered display from the emulator
- audio output from the emulator
- host playback
- listening
- physical hardware

A report supports only the boundary and the target that it measured.
