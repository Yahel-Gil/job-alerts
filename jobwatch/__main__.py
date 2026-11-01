"""
python -m jobwatch --company intel     scan one company, alert on new matching jobs, update state
python -m jobwatch                     same, for every company in config.yaml
python -m jobwatch --dry-run           print every currently open matching job; send nothing, save nothing
python -m jobwatch --digest            daily summary of open matching jobs
python -m jobwatch --test-message      check the Telegram setup

Never applies to anything. It only reads public job lists and sends links.
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone

from . import ai_score, config, filters, notify, state
from .http import session
from .models import SourceError
from .sources import SOURCES

PRUNE_CLOSED_AFTER = timedelta(days=90)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _evaluate(src, s, job, cfg) -> dict:
    tier = filters.tier(job, cfg)
    rec = {
        "title": job.title, "url": job.url, "locations": job.locations, "posted": job.posted,
        "first_seen": _now().isoformat(timespec="seconds"), "open": True,
        "tier": tier, "score": None, "reason": None, "sent": False,
    }
    if tier is None:
        return rec
    hits = filters.domain_hits(job, cfg)
    try:
        description = src.fetch_description(s, job)
    except Exception as e:  # still decide on title alone
        print(f"  description failed for {job.title}: {e}")
        description = ""
    fit = ai_score.score(job, description, config.profile(), cfg["ai"]["model"])
    if fit:
        rec["score"], rec["reason"] = fit.score, fit.reason_he
    rec["sent"] = filters.should_send(tier, hits, rec["score"], cfg)
    return rec


def _health(name: str, error: str | None, cfg: dict, dry_run: bool) -> None:
    h = state.load("health", name) or {"failures": 0, "alerted": False, "last_error": None}
    display = SOURCES[name].DISPLAY
    if error is None:
        if h["alerted"]:
            notify.send(f"✅ הסריקה של {display} חזרה לעבוד.", admin=True, dry_run=dry_run)
        h = {"failures": 0, "alerted": False, "last_error": None}
    else:
        h["failures"] += 1
        h["last_error"] = error[:500]
        if h["failures"] >= cfg["health_alert_after_failures"] and not h["alerted"]:
            notify.send(
                f"⚠️ הסריקה של {display} נכשלה {h['failures']} פעמים ברצף.\n"
                f"ייתכן שהאתר שינה מבנה. עד שזה יתוקן, כדאי לבדוק אותו ידנית.\n\n<code>{notify.esc(error[:300])}</code>",
                admin=True, dry_run=dry_run)
            h["alerted"] = True
    if not dry_run:
        state.save("health", name, h)


def scan(name: str, cfg: dict, dry_run: bool) -> None:
    src = SOURCES[name]
    s = session()
    print(f"== {src.DISPLAY}")
    try:
        jobs = src.fetch_jobs(s)
        if not jobs:
            raise SourceError("0 jobs in Israel")
    except Exception as e:  # any failure here means the site is down, blocking us, or changed
        print(f"  FAILED: {e}")
        _health(name, f"{type(e).__name__}: {e}", cfg, dry_run)
        return
    _health(name, None, cfg, dry_run)

    stored = None if dry_run else state.load("seen", name)
    first_run = stored is None
    seen = stored or {}
    current = {j.id for j in jobs}
    for jid, rec in seen.items():
        rec["open"] = jid in current

    new = [j for j in jobs if j.id not in seen]
    print(f"  {len(jobs)} open in Israel, {len(new)} new")
    matches = []
    for job in new:
        rec = _evaluate(src, s, job, cfg)
        seen[job.id] = rec
        if rec["sent"]:
            matches.append((job.id, rec))
            print(f"  MATCH [{rec['tier']}] {rec['title']} score={rec['score']}")

    if first_run and not dry_run:
        head = f"👋 התחלתי לעקוב אחרי משרות ב-<b>{src.DISPLAY}</b> בישראל ({len(jobs)} משרות פתוחות)."
        body = ("משרות מתאימות שכבר פתוחות עכשיו:\n\n" + "\n\n".join(notify.job_block(r, src.DISPLAY, header=False) for _, r in matches)
                if matches else "כרגע אין משרה מתאימה. אודיע ברגע שתעלה.")
        notify.send(f"{head}\n\n{body}")
    else:
        for jid, rec in matches:
            try:
                notify.send(notify.job_block(rec, src.DISPLAY), dry_run=dry_run)
            except Exception as e:
                print(f"  telegram failed, will retry next run: {e}")
                del seen[jid]

    cutoff = (_now() - PRUNE_CLOSED_AFTER).isoformat()
    seen = {k: v for k, v in seen.items() if v["open"] or v["first_seen"] > cutoff}
    if not dry_run:
        state.save("seen", name, seen)


def digest(cfg: dict, dry_run: bool) -> None:
    since = (_now() - timedelta(days=1)).isoformat()
    sections, total, warnings = [], 0, []
    for name in cfg["companies"]:
        display = SOURCES[name].DISPLAY
        recs = [r for r in (state.load("seen", name) or {}).values() if r["sent"] and r["open"]]
        recs.sort(key=lambda r: (r["tier"] != "student", -(r["score"] or 0)))
        if recs:
            total += len(recs)
            blocks = [("🆕 " if r["first_seen"] > since else "") + notify.job_block(r, display, header=False) for r in recs]
            sections.append(f"<b>━━ {display} ({len(recs)}) ━━</b>\n\n" + "\n\n".join(blocks))
        h = state.load("health", name) or {}
        if h.get("failures"):
            warnings.append(f"⚠️ {display}: {h['failures']} כשלונות ברצף")
    if total:
        text = f"📋 <b>סיכום יומי: {total} משרות מתאימות פתוחות</b>\n\n" + "\n\n".join(sections)
    else:
        text = "📋 <b>סיכום יומי</b>\nכרגע אין משרות פתוחות מתאימות. המערכת ממשיכה לסרוק ✅"
    if warnings:
        text += "\n\n" + "\n".join(warnings)
    notify.send(text, dry_run=dry_run)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--company", choices=sorted(SOURCES))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--digest", action="store_true")
    ap.add_argument("--test-message", action="store_true")
    args = ap.parse_args()
    cfg = config.load()

    if args.test_message:
        notify.send("✅ בדיקה: הבוט של התראות המשרות מחובר ועובד.")
    elif args.digest:
        digest(cfg, args.dry_run)
    else:
        for name in [args.company] if args.company else cfg["companies"]:
            scan(name, cfg, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
