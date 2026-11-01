import re

from .models import Job


def _any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def tier(job: Job, cfg: dict) -> str | None:
    """'student', 'junior', or None (not relevant). Structured site flags win over title words."""
    title = job.title
    if job.tier_hint == "student" or _any(cfg["student_patterns"], title):
        return "student"
    if _any(cfg["senior_patterns"], title):
        return None
    if job.tier_hint == "junior" or _any(cfg["junior_patterns"], title):
        return "junior"
    return None


def domain_hits(job: Job, cfg: dict) -> list[str]:
    text = f"{job.title} {job.team or ''}"
    return [k for k in cfg["domain_keywords"] if re.search(rf"(?<![a-z]){re.escape(k)}(?![a-z])", text, re.IGNORECASE)]


def should_send(tier_: str | None, hits: list[str], score: int | None, cfg: dict) -> bool:
    """score is None when AI scoring is unavailable; then we lean towards sending so nothing is missed."""
    ai = cfg["ai"]
    if tier_ == "student":
        if hits:
            return True
        return score is None or score >= ai["student_without_domain_min_score"]
    if tier_ == "junior":
        return bool(hits) and (score is None or score >= ai["junior_min_score"])
    return False
