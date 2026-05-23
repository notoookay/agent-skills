# agent-skills

**Personal agent skills, packaged to the [agentskills.io](https://agentskills.io) open standard.** Drop-in compatible with any agent runtime that loads `SKILL.md`-format skills — Hermes Agent, Claude Code, and others.

Shaped around one person's workflows (mine) — published openly for transparency and so others can crib patterns, but **not maintained as a community project**. If you want broadly-useful skills, check each agent runtime's own bundled skills first.

## Layout

Each skill is a directory containing a `SKILL.md` (frontmatter + prose) and any `scripts/`, `references/`, or `assets/` it needs. The category layer (`productivity/`, etc.) is convention, not required by the standard.

## What's a "skill"?

A self-contained folder describing a capability — what env vars / CLIs it needs, how to invoke it, and (optionally) helper scripts. The runtime reads `SKILL.md` and exposes the skill to the agent. See [agentskills.io](https://agentskills.io) for the spec.

## Install

Clone wherever you keep code:

```bash
git clone https://github.com/notoookay/agent-skills.git ~/code/agent-skills
```

Then expose individual skill folders to your agent of choice. Examples:

**Hermes Agent**
```bash
mkdir -p ~/.hermes/skills/productivity
ln -s ~/code/agent-skills/productivity/ticktick ~/.hermes/skills/productivity/ticktick
```

**Claude Code**
```bash
mkdir -p ~/.claude/skills
ln -s ~/code/agent-skills/productivity/ticktick ~/.claude/skills/ticktick
```

Symlinks (not copies) so `git pull` is the only sync step.

## Per-skill setup

Each skill has its own `SKILL.md` with prerequisites (env vars, OAuth flows). Check those before first use.

## Secrets

Nothing sensitive is committed. OAuth tokens, API keys, and client secrets live in:
- Env vars on the host (your shell rc, or your runtime's `.env`)
- Per-runtime state directories (e.g. `~/.hermes/state/<skill>/…`, with `0600` perms on token files)

If you fork or copy a skill, double-check `.gitignore` covers any local cache files the skill writes.
