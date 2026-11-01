"""Microsoft careers (apply.careers.microsoft.com, Eightfold "pcsx" API).

- Israel filter: `location=Israel` on GET /api/pcsx/search, sorted by timestamp, 10 per page via `start`.
- The API also mixes in remote roles (`includeRemote`), so we re-check that a location says Israel.
- Without a browser User-Agent the API sometimes answers with an empty body; http.get_json retries.
- No structured student flag; interns are titled "... INTERN" / "Internship Opportunities".
- Apply link: https://apply.careers.microsoft.com/careers/job/{id}
"""
from datetime import datetime, timezone

from ..http import get_json
from ..models import Job

NAME = "microsoft"
DISPLAY = "Microsoft"
SEARCH = "https://apply.careers.microsoft.com/api/pcsx/search"
DETAILS = "https://apply.careers.microsoft.com/api/pcsx/position_details"
PAGE = 10


def _page(s, start: int) -> dict:
    params = {"domain": "microsoft.com", "query": "", "location": "Israel", "start": start, "sort_by": "timestamp"}
    return get_json(s, "GET", SEARCH, params=params)["data"]


def fetch_jobs(s) -> list[Job]:
    first = _page(s, 0)
    total = first.get("count", 0)
    rows = list(first.get("positions", []))
    while len(rows) < total:
        more = _page(s, len(rows)).get("positions", [])
        if not more:
            break
        rows.extend(more)

    jobs = []
    for r in rows:
        locs = r.get("locations", [])
        if not any("israel" in l.lower() for l in locs):
            continue
        ts = r.get("postedTs")
        jobs.append(Job(
            company=NAME,
            id=str(r["id"]),
            title=r["name"],
            locations=[l.replace("Israel, ", "") for l in locs],
            url=f'https://apply.careers.microsoft.com/careers/job/{r["id"]}',
            posted=datetime.fromtimestamp(ts, timezone.utc).date().isoformat() if ts else None,
            team=r.get("department"),
        ))
    return jobs


def fetch_description(s, job: Job) -> str:
    d = get_json(s, "GET", DETAILS, params={"position_id": job.id, "domain": "microsoft.com"})["data"]
    return d.get("jobDescription", "")
