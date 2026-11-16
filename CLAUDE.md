# Claude Code

@AGENTS.md

## Skills

This repository keeps its skills in `.agents/skills/`, a location shared by all
coding agents, not in `.claude/skills/`. Claude Code does not discover them
there on its own, so:

1. At the start of a session, list `.agents/skills/*/SKILL.md` and read the
   `name` and `description` in each file's front matter.
2. When a task matches a description, read that `SKILL.md` in full before
   starting, and follow it as you would an activated skill.
3. Resolve the skill's `references/` and `scripts/` paths from its own folder.
