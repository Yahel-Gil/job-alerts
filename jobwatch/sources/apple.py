"""Apple careers (jobs.apple.com, its own JSON API).

- Israel filter: `filters.locations = ["postLocation-ISR"]` on POST /api/v1/search, sorted newest,
  20 results per page, `totalRecords` gives the count.
- The same role appears once per city (Haifa, Herzliya, Jerusalem...), so results are merged
  by `positionId` and all cities are kept.
- The site's text search is unreliable for us ("student" returns 0 in Israel), so we take every
  Israeli role and filter ourselves.
- Apply link: https://jobs.apple.com/en-il/details/{positionId}/{transformedPostingTitle}
"""
from ..http import get_json
from ..models import Job, SourceError

NAME = "apple"
DISPLAY = "Apple"
SEARCH = "https://jobs.apple.com/api/v1/search"
DETAILS = "https://jobs.apple.com/api/v1/jobDetails/{}"


def _page(s, page: int) -> dict:
    # Apple silently returns 0 results when `format` is missing.
    body = {"query": "", "filters": {"locations": ["postLocation-ISR"]}, "page": page, "locale": "en-us",
            "sort": "newest", "format": {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"}}
    res = get_json(s, "POST", SEARCH, json=body)["res"]
    if page == 1 and not res.get("totalRecords"):
        raise SourceError("Apple: 0 roles in Israel. The search API probably changed")
    return res


def fetch_jobs(s) -> list[Job]:
    first = _page(s, 1)
    total = first.get("totalRecords", 0)
    rows = list(first.get("searchResults", []))
    page = 1
    while len(rows) < total:
        page += 1
        more = _page(s, page).get("searchResults", [])
        if not more:
            break
        rows.extend(more)

    jobs: dict[str, Job] = {}
    for r in rows:
        pid = r["positionId"]
        cities = [l.get("name", "") for l in r.get("locations", [])]
        if pid in jobs:
            jobs[pid].locations += [c for c in cities if c not in jobs[pid].locations]
            continue
        kind = f'{r.get("type", "")} {r.get("jobType", "")}'.lower()
        jobs[pid] = Job(
            company=NAME,
            id=pid,
            title=r["postingTitle"],
            locations=cities,
            url=f'https://jobs.apple.com/en-il/details/{pid}/{r.get("transformedPostingTitle", "")}',
            posted=(r.get("postDateInGMT") or "")[:10] or None,
            tier_hint="student" if "intern" in kind or "student" in kind else None,
            team=(r.get("team") or {}).get("teamName"),
        )
    return list(jobs.values())


def fetch_description(s, job: Job) -> str:
    d = get_json(s, "GET", DETAILS.format(job.id))["res"]
    parts = [d.get(k) or "" for k in ("jobSummary", "description", "minimumQualifications", "preferredQualifications")]
    return "\n\n".join(p for p in parts if p)
