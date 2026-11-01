"""Intel careers (Workday, site External).

- Intel has no country facet. Israel = every value of the `locations` facet whose name starts with
  "Israel," (today: Haifa, Jerusalem, Kiryat-Gat, Petah-Tikva). Read fresh each run, so a new
  Israeli site is picked up automatically.
- Students are marked twice: `workerSubType` = "Student / Intern (Fixed Term)" and
  `jobFamilyGroup` = "Intern". Either one counts.
"""
from ..models import Job, SourceError
from . import _workday_http as wd

NAME = "intel"
DISPLAY = "Intel"
HOST, TENANT, SITE = "intel.wd1.myworkdayjobs.com", "intel", "External"
BASE = wd.base_url(HOST, TENANT, SITE)


def _israel(facets):
    ids = wd.facet_ids(facets, "locations", lambda d: d.lower().startswith("israel"))
    if not ids:
        raise SourceError("Intel: no 'Israel, ...' values in facet locations. Site structure changed?")
    return {"locations": ids}


def _is_student(d: str) -> bool:
    d = d.lower()
    return "student" in d or "intern" in d


def _is_junior(d: str) -> bool:
    d = d.lower()
    return "graduate" in d or "new college" in d


def fetch_jobs(s) -> list[Job]:
    israel = _israel(wd.search(s, BASE, {}).get("facets", []))
    postings, facets = wd.all_postings(s, BASE, israel)
    student = (wd.tagged_paths(s, BASE, israel, "workerSubType", wd.facet_ids(facets, "workerSubType", _is_student))
               | wd.tagged_paths(s, BASE, israel, "jobFamilyGroup", wd.facet_ids(facets, "jobFamilyGroup", _is_student)))
    junior = wd.tagged_paths(s, BASE, israel, "workerSubType", wd.facet_ids(facets, "workerSubType", _is_junior))
    jobs = []
    for p in postings:
        path = p["externalPath"]
        jobs.append(Job(
            company=NAME,
            id=path,
            title=p["title"],
            locations=[p.get("locationsText", "")],
            url=f"https://{HOST}/{SITE}{path}",
            posted=p.get("postedOn"),
            tier_hint="student" if path in student else "junior" if path in junior else None,
        ))
    return jobs


def fetch_description(s, job: Job) -> str:
    return wd.job_detail(s, BASE, job.id).get("jobDescription", "")
