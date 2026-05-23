#!/usr/bin/env python3
"""TickTick API CLI for the Hermes ticktick skill.

Subcommands: whoami, list-projects, list-tasks, create-task, complete-task,
delete-task, raw. Stdlib only. Token refresh handled automatically.

See SKILL.md in the parent directory for setup and full usage.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://ticktick.com/open/v1"
TOKEN_URL = "https://ticktick.com/oauth/token"
DEFAULT_TOKENS = Path.home() / ".hermes" / "state" / "ticktick" / "tokens.json"


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def _tokens_path() -> Path:
    raw = os.environ.get("TICKTICK_TOKENS_PATH")
    return Path(raw).expanduser() if raw else DEFAULT_TOKENS


def _load_tokens() -> dict:
    path = _tokens_path()
    if not path.exists():
        sys.exit(
            f"TickTick is not authorised. Run scripts/auth.py once "
            f"(expected token file at {path})."
        )
    return json.loads(path.read_text())


def _save_tokens(tokens: dict) -> None:
    path = _tokens_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2))
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _refresh(refresh_token: str) -> dict:
    cid = os.environ.get("TICKTICK_CLIENT_ID", "").strip()
    sec = os.environ.get("TICKTICK_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        sys.exit("TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET must be set to refresh tokens.")

    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()

    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, TOKEN_URL, cid, sec)
    opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(mgr))
    req = urllib.request.Request(
        TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with opener.open(req, timeout=20) as resp:
            new = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        sys.exit(
            f"Token refresh failed: HTTP {exc.code} — re-run auth.py.\n"
            f"{exc.read().decode(errors='replace')}"
        )
    new["expires_at"] = time.time() + new.get("expires_in", 3600)
    # Refresh response may omit refresh_token — keep the old one if so.
    new.setdefault("refresh_token", refresh_token)
    _save_tokens(new)
    return new


def _access_token() -> str:
    tokens = _load_tokens()
    if time.time() < tokens.get("expires_at", 0) - 60:
        return tokens["access_token"]
    refreshed = _refresh(tokens["refresh_token"])
    return refreshed["access_token"]


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _request(method: str, path: str, *, payload: Any = None) -> Any:
    url = f"{API_BASE}{path}" if path.startswith("/") else f"{API_BASE}/{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        sys.exit(f"TickTick API error: HTTP {exc.code} {exc.reason}\n{body}")
    except urllib.error.URLError as exc:
        sys.exit(f"Network error talking to TickTick: {exc.reason}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _local_tz_name() -> str:
    """Return an IANA timezone name (e.g. 'America/Los_Angeles') from /etc/localtime.

    Falls back to 'UTC' if the platform doesn't expose the symlink (Windows).
    """
    try:
        link = os.path.realpath("/etc/localtime")
        marker = "zoneinfo/"
        idx = link.find(marker)
        if idx != -1:
            return link[idx + len(marker):]
    except OSError:
        pass
    return "UTC"


def _format_due(iso: str) -> str:
    """Convert any ISO 8601 string into TickTick's UTC `+0000` form."""
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.astimezone()  # assume local
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_whoami(_: argparse.Namespace) -> None:
    projects = _request("GET", "/project") or []
    names = [p.get("name") for p in projects[:5]]
    print(json.dumps({
        "tokens_path": str(_tokens_path()),
        "project_count": len(projects),
        "first_projects": names,
    }, indent=2))


def cmd_list_projects(_: argparse.Namespace) -> None:
    print(json.dumps(_request("GET", "/project"), indent=2))


def cmd_list_tasks(args: argparse.Namespace) -> None:
    # `/project/inbox/data` is the special endpoint for the Inbox; for any
    # other project the id goes in the URL. TickTick does not expose the
    # Inbox in `/project`, so falling back via that path doesn't work.
    path = f"/project/{args.project}/data" if args.project else "/project/inbox/data"
    data = _request("GET", path) or {}
    print(json.dumps(data.get("tasks", []), indent=2))


def cmd_create_task(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {"title": args.title}
    if args.notes:
        payload["content"] = args.notes
    if args.priority is not None:
        payload["priority"] = args.priority
    if args.project:
        payload["projectId"] = args.project
    if args.due:
        payload["dueDate"] = _format_due(args.due)
        payload["timeZone"] = _local_tz_name()
        if not args.no_reminder:
            payload["reminders"] = ["TRIGGER:PT0S"]
    print(json.dumps(_request("POST", "/task", payload=payload), indent=2))


def cmd_complete_task(args: argparse.Namespace) -> None:
    _request("POST", f"/project/{args.project_id}/task/{args.id}/complete")
    print(json.dumps({"ok": True, "id": args.id}, indent=2))


def cmd_delete_task(args: argparse.Namespace) -> None:
    _request("DELETE", f"/project/{args.project_id}/task/{args.id}")
    print(json.dumps({"ok": True, "id": args.id}, indent=2))


def cmd_raw(args: argparse.Namespace) -> None:
    payload = json.loads(args.data) if args.data else None
    result = _request(args.method.upper(), args.path, payload=payload)
    print(json.dumps(result, indent=2) if not isinstance(result, str) else result)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ticktick_api", description="TickTick API CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami").set_defaults(func=cmd_whoami)
    sub.add_parser("list-projects").set_defaults(func=cmd_list_projects)

    lt = sub.add_parser("list-tasks")
    lt.add_argument("--project", help="Project id (defaults to Inbox).")
    lt.set_defaults(func=cmd_list_tasks)

    ct = sub.add_parser("create-task")
    ct.add_argument("--title", required=True)
    ct.add_argument("--due", help="ISO 8601 datetime with UTC offset, e.g. 2026-05-21T18:00:00+09:00")
    ct.add_argument("--notes", default="")
    ct.add_argument("--priority", type=int, choices=[0, 1, 3, 5], default=None)
    ct.add_argument("--project", help="Project id (defaults to Inbox if omitted).")
    ct.add_argument("--no-reminder", action="store_true",
                    help="Do not attach a fire-at-due-time reminder when --due is set.")
    ct.set_defaults(func=cmd_create_task)

    cmp_ = sub.add_parser("complete-task")
    cmp_.add_argument("--id", required=True)
    cmp_.add_argument("--project-id", required=True)
    cmp_.set_defaults(func=cmd_complete_task)

    dl = sub.add_parser("delete-task")
    dl.add_argument("--id", required=True)
    dl.add_argument("--project-id", required=True)
    dl.set_defaults(func=cmd_delete_task)

    raw = sub.add_parser("raw", help="Send an arbitrary request: METHOD PATH [--data JSON]")
    raw.add_argument("method")
    raw.add_argument("path")
    raw.add_argument("--data", help="JSON body string.")
    raw.set_defaults(func=cmd_raw)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
