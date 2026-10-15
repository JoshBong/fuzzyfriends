from __future__ import annotations

import json
import smtplib
import subprocess
import sys
import urllib.request
from email.message import EmailMessage


def send(cfg: dict, title: str, body: str, click: str = "") -> list[str]:
    """Fan out to every enabled channel. Returns errors (never raises)."""
    n = cfg["notify"]
    errors = []
    for name, fn in (("ntfy", _ntfy), ("email", _email), ("desktop", _desktop)):
        if n[name].get("enabled"):
            try:
                fn(n[name], title, body, click)
            except Exception as e:
                errors.append(f"{name}: {e}")
    return errors


def _ntfy(c: dict, title: str, body: str, click: str) -> None:
    if not c.get("topic"):
        raise ValueError("no topic set")
    # JSON publish keeps emoji/UTF-8 out of HTTP headers
    msg = {"topic": c["topic"], "title": title, "message": body, "tags": ["paw_prints"]}
    if click:
        msg["click"] = click
    req = urllib.request.Request(c["server"].rstrip("/"), data=json.dumps(msg).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()


def _email(c: dict, title: str, body: str, click: str) -> None:
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = title, c["user"], c.get("to") or c["user"]
    m.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(c["user"], c["app_password"])
        s.send_message(m)


def _desktop(c: dict, title: str, body: str, click: str) -> None:
    if sys.platform == "darwin":
        script = f"display notification {json.dumps(body[:200], ensure_ascii=False)} with title {json.dumps(title, ensure_ascii=False)} sound name \"Glass\""
        subprocess.run(["osascript", "-e", script], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["notify-send", title, body[:200]], check=False)
