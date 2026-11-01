"""Applied Materials careers (Workday, site External).

- Israel filter: facet `Country` = "Israel" (Rehovot, Kiryat Gat, Migdal HaEmek).
  Location text looks like "Rehovot,ISR".
- Unfiltered search is capped at 2000 results and AMAT has more, so the filter is mandatory.
- `workerSubType` in Israel today: "Assignee / Regular", "New College Grad", "Fixed Term".
  "Fixed Term" is not a reliable student marker here, so students are caught by title + AI instead.
"""
from ..models import Job, SourceError
from . import _workday_http as wd

NAME = "amat"
DISPLAY = "Applied Materials"
HOST, TENANT, SITE = "amat.wd1.myworkdayjobs.com", "amat", "External"
BASE = wd.base_url(HOST, TENANT, SITE)


def _israel(facets):
    ids = wd.facet_ids(facets, "Country", lambda d: d.strip().lower() == "israel")
    if not ids:
        raise SourceError("Applied Materials: no 'Israel' value in facet Country. Site structure changed?")
    return {"Country": ids}


def _is_student(d: str) -> bool:
    d = d.lower()
    return "student" in d or "intern" in d


def _is_junior(d: str) -> bool:
    return "new college" in d.lower()


def fetch_jobs(s) -> list[Job]:
    israel = _israel(wd.search(s, BASE, {}).get("facets", []))
    postings, facets = wd.all_postings(s, BASE, israel)
    student = wd.tagged_paths(s, BASE, israel, "workerSubType", wd.facet_ids(facets, "workerSubType", _is_student))
    junior = wd.tagged_paths(s, BASE, israel, "workerSubType", wd.facet_ids(facets, "workerSubType", _is_junior))
    jobs = []
    for p in postings:
        path = p["externalPath"]
        jobs.append(Job(
            company=NAME,
            id=path,
            title=p["title"],
            locations=[p.get("locationsText", "").replace(",ISR", "")],
            url=f"https://{HOST}/{SITE}{path}",
            posted=p.get("postedOn"),
            tier_hint="student" if path in student else "junior" if path in junior else None,
        ))
    return jobs


def fetch_description(s, job: Job) -> str:
    return wd.job_detail(s, BASE, job.id).get("jobDescription", "")
