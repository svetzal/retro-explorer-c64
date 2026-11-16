# Projects

Each project that the owner builds is in its own folder here. The folder name
is the idea in a few lowercase words joined by hyphens, such as
`bouncing-lines`.

A project folder holds:

- `README.md`: what the owner asked for and how to run it in plain language,
  then the project contract that the agent works from.
- `main.asm`: the program.
- `c64.toml`: the target, firmware, memory layout and check settings.
- `expected.py`: an independent model of what the program must produce.
- Input scripts and assets, when the project needs them.

To start a project, copy [`template/`](../template/README.md) to a new folder
here. Do not copy an example folder. Each example shows one practice. Use it
as a reference.

Build, run and check a project with this command:

```sh
uv run python scripts/c64.py <command> projects/<name>
```

[Development practice](../guidance/starter/development.md) describes the
contract and the checks. The starter keeps only this file and
[AGENTS.md](AGENTS.md) here. Your projects are yours.
