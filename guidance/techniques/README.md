# Techniques for games and demos

Start with the effect that you want. Each guide explains a practical approach,
credits its sources and states what has been tested. Read one guide at a
time. Each guide ends with its sources and open questions.

| I want to… | Read | Current evidence |
| --- | --- | --- |

There are no technique guides yet. Until there are, use the
[reference lookup](../starter/references.md) procedure for each
hardware-dependent fact, and say that no guide covers the work.

## How guides get here

A guide comes from real work, not from a plan to write guides. There are two
ways:

- **A lab.** A BUILD problem has no answer in the guides. The owner agrees to
  a lab. The lab finds an answer and codifies it as a guide, an example or a
  tool ability. Read [the lab procedure](../starter/lab.md).
- **BUILD work.** A project uses a technique that is sourced and checked, and
  the next project could use it again. Write the guide from the sources and
  the check, not from the project's code alone.

Write each guide to the [guide contract](../AGENTS.md#guide-contract). Then
add one row to the table above:

- **I want to…** names the effect in the owner's words, such as "Move objects
  over scenery".
- **Read** links to the guide.
- **Current evidence** names the example and the targets that its check
  covers, the controls that must fail, and what remains untested.

## Read the evidence correctly

**Published explanation** means that we examined the cited passage. It does
not mean that we ran its program, or that we know who invented the idea.
**Our adaptation** means that the starter's authors derived the advice or
procedure. **Measured result** means that a linked example or check measured
a stated outcome. A proposal stays untested until a check supplies that
evidence.

Citations are beside the claims that they support. PDF page numbers are
one-based positions in the source file. Printed page numbers appear
separately when known. Resource IDs resolve to locations and checksums in
`resources.json`.

These guides explain techniques in our own words. They do not redistribute
books, magazine listings, music or art. The availability of a file in an
archive grants no licence to reuse its code or assets.

## Before you write a game

Read the selected guide. Then read its cited hardware passages for your
target. Record the machine choices in the project contract, as
[development practice](../starter/development.md#establish-the-contract)
describes. Keep unresolved details visible. Do not fill gaps from model
memory.

Treat each of these as separate evidence:

- an assembled program
- emulator execution
- visible output
- audible output
- physical-machine behaviour

BASIC articles can explain useful ideas. Their firmware calls, storage
formats and performance do not transfer to assembly language.
