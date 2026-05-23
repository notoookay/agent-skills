#!/usr/bin/env python3
"""One-time OAuth 2.0 setup for the TickTick skill.

Usage:
    python3 auth.py            # local: opens browser + starts callback server on :8080
    python3 auth.py --manual   # server: prints URL, you paste the redirected URL back

Reads TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET, optionally TICKTICK_REDIRECT_URI
and TICKTICK_TOKENS_PATH. Writes tokens (0600) to
~/.hermes/state/ticktick/tokens.json by default.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

AUTH_URL = "https://ticktick.com/oauth/authorize"
TOKEN_URL = "https://ticktick.com/oauth/token"
DEFAULT_REDIRECT = "http://localhost:8080/callback"
DEFAULT_TOKENS = Path.home() / ".hermes" / "state" / "ticktick" / "tokens.json"


def _redirect_uri() -> str:
    return os.environ.get("TICKTICK_REDIRECT_URI", DEFAULT_REDIRECT)


def _tokens_path() -> Path:
    raw = os.environ.get("TICKTICK_TOKENS_PATH")
    return Path(raw).expanduser() if raw else DEFAULT_TOKENS


def _require_credentials() -> tuple[str, str]:
    cid = os.environ.get("TICKTICK_CLIENT_ID", "").strip()
    sec = os.environ.get("TICKTICK_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        sys.exit("TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET must be set as env vars.")
    return cid, sec


def _is_headless() -> bool:
    if sys.platform == "darwin" or sys.platform.startswith("win"):
        return False
    return not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")


def _save_tokens(tokens: dict) -> Path:
    path = _tokens_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    path.write_text(json.dumps(tokens, indent=2))
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def _exchange_code(code: str) -> None:
    cid, sec = _require_credentials()
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _redirect_uri(),
    }).encode()

    basic = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    basic.add_password(None, TOKEN_URL, cid, sec)
    handler = urllib.request.HTTPBasicAuthHandler(basic)
    opener = urllib.request.build_opener(handler)

    req = urllib.request.Request(
        TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with opener.open(req, timeout=20) as resp:
            tokens = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        sys.exit(f"Token exchange failed: HTTP {exc.code} — {exc.read().decode(errors='replace')}")

    path = _save_tokens(tokens)
    print(f"TickTick authorised. Tokens saved to {path}")


_captured: dict[str, str | None] = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 — required by BaseHTTPRequestHandler
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _captured["code"] = qs.get("code", [None])[0]
        _captured["error"] = qs.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<h2>Authorised. You can close this tab and return to Hermes.</h2>"
        )

    def log_message(self, *_):  # silence default access log
        pass


def _run_automatic(auth_url: str) -> None:
    print("Opening TickTick authorisation page…")
    print(f"If it doesn't open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    redirect = urllib.parse.urlparse(_redirect_uri())
    port = redirect.port or 8080
    server = HTTPServer(("localhost", port), _CallbackHandler)
    server.handle_request()  # blocks for one request

    if _captured.get("error"):
        sys.exit(f"TickTick auth failed: {_captured['error']}")
    code = _captured.get("code")
    if not code:
        sys.exit("No authorisation code received.")
    _exchange_code(code)


def _run_manual(auth_url: str) -> None:
    print("=== TickTick manual authorisation ===\n")
    print("1. Open this URL in any browser:")
    print(f"\n  {auth_url}\n")
    print("2. Authorise the app.")
    print("3. You'll be redirected to a localhost URL that fails to load — that's expected.")
    print("   Copy the full URL from the browser and paste it below.")
    print("   (looks like: http://localhost:8080/callback?code=XXXX&state=hermes)\n")

    raw = input("Paste the redirect URL (or just the code): ").strip()
    if raw.startswith("http"):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        if qs.get("error", [None])[0]:
            sys.exit(f"TickTick auth failed: {qs['error'][0]}")
        code = qs.get("code", [None])[0]
    else:
        code = raw
    if not code:
        sys.exit("No authorisation code found in the pasted value.")
    _exchange_code(code)


def main() -> None:
    cid, _ = _require_credentials()
    params = {
        "client_id": cid,
        "response_type": "code",
        "scope": "tasks:read tasks:write",
        "redirect_uri": _redirect_uri(),
        "state": "hermes",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    if "--manual" in sys.argv or _is_headless():
        _run_manual(auth_url)
    else:
        _run_automatic(auth_url)


if __name__ == "__main__":
    main()
