"""Amazon jobs (www.amazon.jobs, its own JSON search), including Annapurna Labs.

- Israel filter: `normalized_country_code[]=ISR` on GET /en/search.json, sorted recent,
  at most 100 results per page via `offset`, `hits` gives the count.
- The search result already holds the full description and qualifications, so no second request.
- `is_intern` / `university_job` are always empty in Israel; students are titled "... Student" / "Intern".
- `job_category` (e.g. "Hardware Development") is kept as the team for keyword matching.
- Apply link: https://www.amazon.jobs{job_path}
"""
from datetime import datetime

from ..http import get_json
from ..models import Job, SourceError

NAME = "amazon"
DISPLAY = "Amazon"
SEARCH = "https://www.amazon.jobs/en/search.json"
PAGE = 100


def _page(s, offset: int) -> dict:
    params = {"normalized_country_code[]": "ISR", "result_limit": PAGE, "offset": offset, "sort": "recent"}
    return get_json(s, "GET", SEARCH, params=params)


def _date(text: str) -> str | None:
    try:
        return datetime.strptime(" ".join(text.split()), "%B %d, %Y").date().isoformat()
    except (ValueError, AttributeError):
        return text or None


def fetch_jobs(s) -> list[Job]:
    first = _page(s, 0)
    total = first.get("hits") or 0
    if not total:
        raise SourceError("Amazon: 0 roles in Israel. The search API probably changed")
    rows = list(first.get("jobs") or [])
    while len(rows) < total:
        more = _page(s, len(rows)).get("jobs") or []
        if not more:
            break
        rows.extend(more)

    jobs, ids = [], set()
    for r in rows:
        jid = r["id_icims"]
        if jid in ids or r.get("country_code") != "ISR":  # a posting can move between pages mid-scan
            continue
        ids.add(jid)
        jobs.append(Job(
            company=NAME,
            id=jid,
            title=r["title"].strip(),
            locations=[r.get("city") or r.get("location", "")],
            url=f'https://www.amazon.jobs{r["job_path"]}',
            posted=_date(r.get("posted_date")),
            team=r.get("job_category"),
            extra={"description": "\n\n".join(
                r.get(k) or "" for k in ("description", "basic_qualifications", "preferred_qualifications"))},
        ))
    return jobs


def fetch_description(s, job: Job) -> str:
    return job.extra.get("description", "")
