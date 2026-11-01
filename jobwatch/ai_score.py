"""Optional fit score from Claude. Any failure returns None and the caller falls back to keywords."""
import html
import os
import re

import anthropic
from pydantic import BaseModel, Field

from .models import Job

SYSTEM = (
    "You screen job postings for one candidate. Compare the posting with the candidate profile and "
    "rate how well it fits on a 1-10 scale, where 10 means a student/intern hardware or validation role "
    "she clearly qualifies for, and 1 means unrelated or requiring years of experience. "
    "Write the reason in Hebrew, one short sentence, addressed to the candidate in the feminine form."
)


class Fit(BaseModel):
    score: int = Field(ge=1, le=10)
    reason_he: str
    is_student_role: bool


def _plain(text: str) -> str:
    text = re.sub(r"<br\s*/?>|</p>|</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def score(job: Job, description: str, profile: str, model: str) -> Fit | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    prompt = (
        f"<profile>\n{profile}\n</profile>\n\n"
        f"<posting company=\"{job.company}\" title=\"{job.title}\" locations=\"{', '.join(job.locations)}\">\n"
        f"{_plain(description)}\n</posting>"
    )
    try:
        resp = anthropic.Anthropic().messages.parse(
            model=model,
            max_tokens=1024,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_format=Fit,
            output_config={"effort": "low"},
        )
    except anthropic.APIError as e:
        print(f"  AI scoring failed for {job.title}: {e}")
        return None
    if resp.stop_reason == "refusal":
        return None
    return resp.parsed_output
