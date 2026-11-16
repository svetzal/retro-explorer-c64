# Build something for the Commodore 64

Make a game, animation or experiment for the Commodore 64 with your coding
agent. This starter gives your agent project guidance, tools and a way to read
original reference material. You bring the idea.

You do not need to know assembly language or prepare a development
environment before you start. Ask your agent to do the setup as part of your
project.

You can try the result on your current computer in VICE, an emulator that acts
like a C64. You do not need the original hardware. The
[toolchain guide](guidance/starter/toolchain.md#supported-hosts) lists the
computers that the starter supports today.

## Start with your agent

Open Claude Code, Codex, OpenCode or another coding agent that can work with
files and run programs on your computer. A chat window without those
abilities cannot do the setup for you.

Copy this prompt into your agent. Replace the last line with your own idea, or
keep it for a first project:

```text
Start a new project from https://github.com/svetzal/retro-explorer-c64.
Read its AGENTS.md and handle setup for me. I'm a beginner.

Build a C64 animation with a bouncing ball and a colour bar that moves.
```

The repository address is enough for your agent to find the starter. You do
not need to download it yourself or type its setup commands. Your agent may
ask where to put your project, or ask for permission to install tools.

If this starter is already open in your agent, ask it to use the current
folder. Ask it not to make another copy.

## Describe what you want to make

Start with what you want to see or do. For example:

- "Make a game where I steer a ship around the screen with the joystick."
- "Draw a colourful pattern that changes when I press a key."
- "Help me learn how to draw a sprite, one small step at a time."

Tell your agent which kind of C64 you have, if you know it. The C64 was made
for two television standards, PAL and NTSC, and a program can behave
differently on each. The starter has a target for each: `c64-ntsc` and
`c64-pal`. If you are unsure, ask for an NTSC project in the emulator. The
agent has starting defaults for that choice.

Tell your agent if you want to use a real machine. The equipment of that
machine affects what the project can run.

## What happens next

Your agent checks the tools. It prepares the emulator and the references that
your project needs. The first setup can take a while. Later work uses the
same downloads again.

Your agent names your project and keeps it in its own folder, such as
`projects/bouncing-ball`. The README in that folder says what you asked for
and how to run it.

Ask for a small working result before you add more features. Then describe
what you want to change. Keep working in the same starter folder, so your
agent can use your projects and the references again.

## Building, and solving problems in a lab

Your agent works in one of two modes. The first line of each reply tells you
which mode, for example:

```text
BUILD · bouncing-ball
LAB · crackly-sound (from bouncing-ball)
```

**Building** is where you spend most of your time. You describe your game or
demo, and the agent makes it from the starter's guides and examples. Your
project stays in its own folder and grows as you ask for changes.

Sometimes a problem has no ready answer. For example, the sound crackles, the
graphics are too slow, or a joystick move is missed. Then the agent can open a
**lab**. A lab is a separate session that focuses on that one problem. In a
lab the agent does these steps:

1. It writes down the question, such as "why does the sound crackle while the
   screen redraws?"
2. It reads the original books and manuals. It tries small test programs
   until it finds an answer that works.
3. It explains what it found in plain words.
4. It adds the answer to the starter's guides or examples, so this project and
   later projects can use it.
5. It cleans up its test programs. Then it returns to your project to apply
   the fix.

The agent may suggest a lab when it gets stuck, but it waits for you to agree.
You can also ask for one yourself:

> Open a lab: the sound crackles whenever the ball moves.

A lab can take longer than a normal change, because it tests ideas before it
settles on one. You can stop it at any time:

> Close the lab and go back to building.

If you stop partway, your project notes record the open lab. Next time, the
agent asks whether to continue the lab or to continue building. The
improvements that a lab makes stay in your copy of the starter unless you
choose to share them.

## What to expect today

This is a new starter, and it is a concept in development. It has no
technique guides and no worked game yet. Your first projects and labs are
what fill it in.

The C64 had magazines, books and type-in listings everywhere, and people still
write new games and demos for it. A lot of that knowledge is easy to find.
A lot of it is also scattered, or was never written down.

The quality of what you make depends on two things. One is the guides in this
repository, which grow over time. The other is the labs that you start, where
the agent researches your problem. It may find a book, a magazine article or
an old forum post with the answer. Or it may have to put its head down and
work the problem out itself.

Your attention to detail matters, and so does your care for how the game
plays and feels. Those will have far more effect on the result than the agent
does.

Some problems you will not solve. Some you may solve in a way nobody has
published before. Some, someone else solved decades ago. Have fun with it. If
you have trouble, drop me a line.

## Look inside when you are ready

The programs you build are in 6502 assembly language. The C64's 6510
processor runs it. Your agent writes it for you, and you can read it in your
project's `main.asm`.

The starter also has Python code that does the tedious technical steps:
setup, assembly, launching the emulator and checking the results. You never
need to touch that code.

You can start without reading these pages. Choose one when you need it:

- [Examples](examples/README.md) for small programs to build and study.
- [Agent guidance](guidance/README.md): how your agent uses this starter, and
  the techniques that it knows.
- [Agent instructions](AGENTS.md) for starting work.
- [PLAN.md](PLAN.md) for open work.

## References, firmware and licensing

The starter downloads reference books and manuals that are available online.
It uses the firmware that comes with VICE. It keeps the downloads on your
computer, outside the files that Git tracks. The repository does not include
copies of the books or the firmware.

The starter's code and original guidance use the [MIT licence](LICENSE). That
licence does not cover downloaded books, firmware or converted pages. Those
materials keep their own copyright and licensing.
