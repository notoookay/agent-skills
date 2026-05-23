# agent-skills

**Personal skills for [Hermes Agent](https://github.com/NousResearch/hermes-agent).** These are shaped around one person's workflows (mine) — published openly for transparency and so others can crib patterns, but **not maintained as a community project**.

> If you want broadly-useful skills, look at Hermes's bundled `skills/` and `optional-skills/` directories first.

## Layout

```
.
├── productivity/
│   └── ticktick/          # TickTick OAuth task & reminder integration
└── …                      # more categories as I add skills
```

The layout mirrors `~/.hermes/skills/<category>/<skill>/` so each skill folder can be dropped straight into a Hermes install.

## Install on a new machine

```bash
git clone https://github.com/notoookay/agent-skills.git ~/code/agent-skills

# Symlink each category dir's contents into ~/.hermes/skills/<category>/
mkdir -p ~/.hermes/skills/productivity
ln -s ~/code/agent-skills/productivity/ticktick ~/.hermes/skills/productivity/ticktick
```

Symlinks (not copies) so `git pull` in `~/code/agent-skills` is the only sync step. Hermes discovers skills by scanning `~/.hermes/skills/**/SKILL.md` — symlinked directories work the same as real ones.

## Per-skill setup

Each skill folder has its own `SKILL.md` with prerequisites (env vars, OAuth flows, etc.). Check those before first use.

### Current skills

| Skill | Path | Setup |
|---|---|---|
| TickTick | `productivity/ticktick/` | Set `TICKTICK_CLIENT_ID` + `TICKTICK_CLIENT_SECRET`, run `scripts/auth.py` once |

## Secrets

Nothing sensitive is committed. OAuth tokens, API keys, and client secrets live in:
- Env vars on the host (`~/.hermes/.env` or your shell rc)
- Hermes state dir: `~/.hermes/state/<skill>/…` (token files, `0600` perms)

If you fork or copy a skill, double-check `.gitignore` covers any local cache files the skill writes.

## License

MIT — see [LICENSE](LICENSE).
