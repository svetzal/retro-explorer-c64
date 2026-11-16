# Rules for projects

Read this file before you start, change or review a project in `projects/`.
A project is the owner's actual game, animation or experiment. Build what the
owner asked for. Do not turn it into a lesson about every technique that it
uses.

## Start a project

1. Name the folder from the owner's idea: a few lowercase words joined by
   hyphens. Tell the owner the name and where the project is.
2. Never reuse or change another project's folder.
3. Copy [`template/`](../template/README.md) to `projects/<name>/`. Do not
   copy an example folder.
4. Write the README: what the owner asked for, how to run it in plain
   language, and the
   [project contract](../guidance/starter/development.md#establish-the-contract).
   Read the file back.
5. Keep `c64.toml` the same as the contract.

## Keep owner choices and defaults apart

The README records what the owner asked for in the owner's words. The
contract marks each value as an owner requirement, a starter default, or an
agent choice. Do not describe a default or your own choice as the owner's
decision. When the owner changes their mind, update the request and the
contract in place.

## Build in small, checked increments

- Build the smallest complete increment first, then add to it.
- Keep `expected.py` current. Write it from the request and sourced facts,
  not from the program's output.
- Check each feature that you claim with `scripts/c64.py check`. Obey
  [check the feature you claim](../guidance/starter/development.md#check-the-feature-you-claim).
- For a game with opponents, randomness or levels, add
  [test-harness controls](../guidance/starter/development.md#test-harness-controls-for-dynamic-games).
  List them in the README.
- Never call a build alone a working project. Report each untested boundary.

## Open labs

When a lab starts from this project, add an `Open lab: <topic>` line to the
README. Remove the line when the lab closes. When a session starts and the
line is present, ask the owner whether to resume the lab or continue
building. Read [the lab procedure](../guidance/starter/lab.md).

## What stays out

- Research notes, experiment logs and validation reports. They belong in the
  lab folder under ignored `local/lab/`.
- Downloaded books, firmware and converted pages. They stay under `local/`.
- Build products and captures. They stay under `build/`.

Commit the project folder in the owner's copy of the starter. Do not push or
publish the project unless the owner asks.

A project can have its own `AGENTS.md` for constraints that apply only to
that project.
