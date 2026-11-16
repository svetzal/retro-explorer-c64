# Rules for guidance

Read this file before you write, change or review anything in `guidance/`.

## What belongs here

- `starter/` holds procedures for this repository: setup, tools, references,
  development practice and the lab. Read a starter guide to operate the
  repository.
- `techniques/` holds C64 knowledge: how to get an effect on the machine,
  with its sources and its evidence. Read a technique guide to decide how to
  build something.

Keep the two apart. A procedure does not explain the hardware. A technique
guide does not explain how to run the tools. Link to the other part instead.

Research notes, validation reports and experiment logs do not belong here.
They stay in the lab folder under ignored `local/lab/`. A guide records the
result and the check that reproduces it.

## Write every guide in simplified technical English

Read the
[simplified-technical-english](../.agents/skills/simplified-technical-english/SKILL.md)
skill before you write. Run its checker on each file that you change, and fix
what it reports:

```sh
python3 .agents/skills/simplified-technical-english/scripts/ste_check.py <file>
```

## Guide contract

A technique guide tells an agent how to get an effect on the C64. Keep it in
ordinary Markdown in `guidance/techniques/`. A guide of 200 to 300 lines is typical. Keep each guide below 300 lines. Each guide states:

- The task, the targets and configurations it applies to, and their limits.
- Practical steps, memory and timing tradeoffs, and likely failure cases.
- Inline citations beside sourced claims. For a local reference, give the
  author, title, edition or issue, PDF page (printed page when known) and
  resource ID. For a page at a URL, give the author, title, date, URL and
  date read. Add a Wayback Machine link when one exists. Cite only passages
  that you read. Inspect diagrams and listings as images when the conversion
  is uncertain.
- Which claims are published explanations, our adaptations, derived
  calculations, measured results or untested proposals.
- For each measured result, the check that runs it again. If no check can,
  the method to repeat it.
- The example that shows it, and what the check of that example proves.
- Unresolved conflicts and the evidence that would settle them.

Credit the authors that you examined. Do not claim that one of them invented a
technique. Keep copyrighted source content in ignored storage. Publish only
original explanations and source metadata.

[Reference lookup](starter/references.md#cite-each-kind-of-evidence) gives
the form of each kind of citation.

## Keep the index current

When you add or change a technique guide, update its row in the
[technique index](techniques/README.md). The row names the effect, the guide
and the current evidence. Do not claim more evidence in the index than the
guide states.

When you add a starter guide, add a line to the [guidance map](README.md).

## How guidance loses its purpose

Watch for these failures when you review a change:

- A claim that comes from model memory, with no citation and no check.
- A fact from one C64 model that the guide applies to another model without a
  source.
- An emulator result that the guide reports as physical behaviour.
- A guide that copies a book passage instead of explaining it.
- A guide that repeats a procedure from another guide instead of a link.
- A guide that grows past 300 lines. Split it by effect.
