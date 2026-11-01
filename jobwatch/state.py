"""Per-company JSON state under state/. One file per company so parallel runs never touch the same file.

seen_<company>.json: {job_id: {title, url, locations, posted, first_seen, open, tier, score, reason, sent}}
health_<company>.json: {failures, alerted, last_error}
"""
import json

from .config import ROOT

STATE = ROOT / "state"


def _path(kind: str, company: str):
    return STATE / f"{kind}_{company}.json"


def load(kind: str, company: str) -> dict | None:
    p = _path(kind, company)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save(kind: str, company: str, data: dict) -> None:
    STATE.mkdir(exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    p = _path(kind, company)
    if not p.exists() or p.read_text(encoding="utf-8") != text:  # avoid empty commits
        p.write_text(text, encoding="utf-8")
