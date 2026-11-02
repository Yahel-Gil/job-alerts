"""Telegram messages. TELEGRAM_CHAT_ID may hold several ids separated by commas (group or private chats)."""
import html
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from . import config

LIMIT = 4000  # Telegram caps a message at 4096 chars


def _chat_ids(env: str) -> list[str]:
    return [c.strip() for c in os.environ.get(env, "").split(",") if c.strip()]


def send(text: str, *, admin: bool = False, dry_run: bool = False) -> None:
    """admin=True sends health alerts to TELEGRAM_ADMIN_CHAT_ID when set, otherwise to the main chat."""
    if dry_run:
        print("----- telegram (dry run) -----\n" + text + "\n------------------------------")
        return
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()  # secrets pasted in the GitHub UI often keep a trailing newline
    chats = (admin and _chat_ids("TELEGRAM_ADMIN_CHAT_ID")) or _chat_ids("TELEGRAM_CHAT_ID")
    silent = is_quiet_hours()
    for chunk in _chunks(text):
        for chat in chats:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat, "text": chunk, "parse_mode": "HTML",
                      "disable_web_page_preview": True, "disable_notification": silent},
                timeout=30,
            )
            r.raise_for_status()


def is_quiet_hours(now: datetime | None = None) -> bool:
    """At night messages still arrive, just without sound or vibration."""
    q = config.load()["quiet_hours"]
    hour = (now or datetime.now(ZoneInfo(q["timezone"]))).hour
    return hour >= q["start"] or hour < q["end"]


def _chunks(text: str) -> list[str]:
    out, cur = [], ""
    for block in text.split("\n\n"):
        if len(cur) + len(block) + 2 > LIMIT and cur:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n\n{block}" if cur else block
    return out + ([cur] if cur else [])


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def job_block(rec: dict, display: str, *, header: bool = True) -> str:
    badge = "🟢 משרת סטודנט" if rec["tier"] == "student" else "🟡 משרת ג'וניור"
    lines = []
    if header:
        lines.append(f"<b>{badge} חדשה · {esc(display)}</b>")
    lines.append(f"<b>{esc(rec['title'])}</b>")
    where = " · ".join(x for x in [", ".join(rec["locations"]), rec.get("posted") or ""] if x)
    lines.append(f"📍 {esc(where)}")
    if rec.get("score") is not None:
        lines.append(f"⭐ התאמה {rec['score']}/10: {esc(rec.get('reason') or '')}")
    lines.append(f'🔗 <a href="{html.escape(rec["url"])}">לפרטים ולהגשה</a>')
    return "\n".join(lines)
