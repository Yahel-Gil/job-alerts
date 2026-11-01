import os
from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@cache
def load() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


@cache
def profile() -> str:
    """Candidate summary for AI scoring. In GitHub it comes from the encrypted PROFILE_TEXT secret;
    locally from profile.md, which is git-ignored so it never lands in the public repo."""
    text = os.environ.get("PROFILE_TEXT", "").strip()
    if text:
        return text
    local = ROOT / "profile.md"
    return local.read_text(encoding="utf-8") if local.exists() else ""
