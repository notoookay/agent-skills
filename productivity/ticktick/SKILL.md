---
name: ticktick
description: "TickTick: create reminders, list tasks, complete/delete tasks via OAuth 2.0 API."
version: 0.1.0
author: wenyang
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET]
  commands: [python3]
metadata:
  hermes:
    tags: [TickTick, Tasks, Reminders, Productivity, OAuth]
---

# TickTick — Tasks & Reminders

Create, list, complete, and delete TickTick tasks (and time-based reminders) via the official Open API. Stdlib-only Python — no extra dependencies.

## One-time setup

1. **Register an app** at https://developer.ticktick.com/manage → "+ App". Set the redirect URI to `http://localhost:8080/callback`. Copy the client ID and secret.
2. **Set env vars** (via `hermes setup` or your shell rc):
   ```
   TICKTICK_CLIENT_ID=...
   TICKTICK_CLIENT_SECRET=...
   ```
   Optional: `TICKTICK_REDIRECT_URI` (default `http://localhost:8080/callback`), `TICKTICK_TOKENS_PATH` (default `~/.hermes/state/ticktick/tokens.json`).
3. **Authorise once** — opens the browser locally, or use `--manual` on a headless server:
   ```bash
   SCRIPT_DIR=$(dirname "$(find ~/.hermes -path '*skills/productivity/ticktick/scripts/auth.py' 2>/dev/null | head -1)")
   python3 "$SCRIPT_DIR/auth.py"            # local: opens browser + captures callback
   python3 "$SCRIPT_DIR/auth.py" --manual   # server: paste the redirect URL back
   ```
   Tokens land in `~/.hermes/state/ticktick/tokens.json` and refresh automatically on use.

## CLI usage

All API calls go through `scripts/ticktick_api.py`. Resolve the path once, then invoke subcommands:

```bash
SCRIPT=$(find ~/.hermes -path '*skills/productivity/ticktick/scripts/ticktick_api.py' 2>/dev/null | head -1)

python3 "$SCRIPT" whoami                       # sanity check — lists projects
python3 "$SCRIPT" list-projects
python3 "$SCRIPT" list-tasks                   # Inbox by default
python3 "$SCRIPT" list-tasks --project PROJECT_ID
python3 "$SCRIPT" create-task --title "Call dentist" --due 2026-05-21T18:00:00+09:00 --notes "ph: 555-1212"
python3 "$SCRIPT" complete-task --id TASK_ID --project-id PROJECT_ID
python3 "$SCRIPT" delete-task   --id TASK_ID --project-id PROJECT_ID
python3 "$SCRIPT" raw GET  /project                  # escape hatch — any endpoint
python3 "$SCRIPT" raw POST /task --data '{"title":"x"}'
```

All commands print JSON on success, or a human-readable error and exit non-zero on failure.

## Reminders (time-based tasks)

TickTick fires a notification at `dueDate` when a task has at least one `reminders` trigger. `create-task` adds a `TRIGGER:PT0S` reminder by default (fires at the due time). When the user says **"remind me in 2 hours…"** or **"set a reminder for 6pm"**, use `create-task` with `--due` set to an ISO 8601 datetime **with UTC offset** (e.g. `2026-05-21T18:00:00+09:00`).

Resolve relative times (`in 2 hours`, `tomorrow at 9am`) with the agent's date/time tool first, then pass the absolute ISO string. Do **not** ask TickTick to do timezone math — always send an explicit offset.

## API basics

- **Base URL:** `https://ticktick.com/open/v1`
- **Auth header:** `Authorization: Bearer <access_token>` (refresh handled by `ticktick_api.py`)
- **Project ID for the Inbox:** TickTick doesn't expose a stable Inbox ID via `/project` (it's filtered out). The script auto-detects via `/project/inbox/data` and uses that when `--project` is omitted.
- **Priorities:** 0 = none, 1 = low, 3 = medium, 5 = high (TickTick's non-obvious scale)
- **dueDate format on writes:** UTC, formatted `YYYY-MM-DDTHH:MM:SS+0000` (no colon in offset — TickTick is picky)
- **Time zone:** include `"timeZone": "America/Los_Angeles"` (IANA) when creating timed tasks; the script reads `/etc/localtime` to detect this automatically

## Subcommand reference

| Command | Required | Optional | Returns |
|---|---|---|---|
| `whoami` | — | — | JSON: project count + first few project names |
| `list-projects` | — | — | JSON array of projects |
| `list-tasks` | — | `--project ID` (default: Inbox) | JSON array of tasks |
| `create-task` | `--title T` | `--due ISO8601`, `--notes N`, `--priority {0,1,3,5}`, `--project ID`, `--no-reminder` | JSON of created task |
| `complete-task` | `--id`, `--project-id` | — | `{"ok": true}` |
| `delete-task` | `--id`, `--project-id` | — | `{"ok": true}` |
| `raw METHOD PATH` | — | `--data JSON` | Raw response body |

Run any subcommand with `--help` for full flags.

## Troubleshooting

- **`TickTick is not authorised`** → run `auth.py` (see setup step 3).
- **`401 Unauthorized` after refresh** → access + refresh tokens both expired. Re-run `auth.py`.
- **`No display available` on a remote server** → use `auth.py --manual`.
- **Wrong fire time** → the `due_at` string was missing a UTC offset. Always include `+HH:MM` or `Z`.
- **Inbox tasks not appearing in `list-projects`** → expected. The Inbox is virtual; use `list-tasks` with no `--project` to see it.

## Notes

- This skill talks **only** to `ticktick.com` — your task content is not sent anywhere else.
- The token file (`~/.hermes/state/ticktick/tokens.json`) is sensitive; the auth script writes it with `0600` perms.
