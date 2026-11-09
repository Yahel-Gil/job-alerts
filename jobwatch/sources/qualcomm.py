"""Qualcomm careers (careers.qualcomm.com, Eightfold "pcsx" API, same engine as Microsoft).

- Israel filter: `location=Israel` on GET /api/pcsx/search, sorted by timestamp, 10 per page via `start`.
- We re-check that a location says Israel, in case remote roles get mixed in.
- Locations look like "Hod Hasharon, Haifa District, Israel"; only the city is kept.
- Interns sit in the "Engineering Intern" department, used as a structured student flag.
- Apply link: https://careers.qualcomm.com/careers/job/{id}
"""
from datetime import datetime, timezone

from ..http import get_json
from ..models import Job, SourceError

NAME = "qualcomm"
DISPLAY = "Qualcomm"
SEARCH = "https://careers.qualcomm.com/api/pcsx/search"
DETAILS = "https://careers.qualcomm.com/api/pcsx/position_details"


def _page(s, start: int) -> dict:
    params = {"domain": "qualcomm.com", "query": "", "location": "Israel", "start": start, "sort_by": "timestamp"}
    return get_json(s, "GET", SEARCH, params=params)["data"]


def fetch_jobs(s) -> list[Job]:
    first = _page(s, 0)
    total = first.get("count", 0)
    if not total:
        raise SourceError("Qualcomm: 0 roles in Israel. The search API probably changed")
    rows = list(first.get("positions", []))
    while len(rows) < total:
        more = _page(s, len(rows)).get("positions", [])
        if not more:
            break
        rows.extend(more)

    jobs = []
    for r in rows:
        locs = [l for l in r.get("locations", []) if "israel" in l.lower()]
        if not locs:
            continue
        ts = r.get("postedTs")
        dept = r.get("department") or ""
        jobs.append(Job(
            company=NAME,
            id=str(r["id"]),
            title=r["name"].strip(),
            locations=[l.split(",")[0].strip() for l in locs],
            url=f'https://careers.qualcomm.com/careers/job/{r["id"]}',
            posted=datetime.fromtimestamp(ts, timezone.utc).date().isoformat() if ts else None,
            tier_hint="student" if "intern" in dept.lower() else None,
            team=dept or None,
        ))
    return jobs


def fetch_description(s, job: Job) -> str:
    d = get_json(s, "GET", DETAILS, params={"position_id": job.id, "domain": "qualcomm.com"})["data"]
    return d.get("jobDescription", "")
