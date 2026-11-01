"""NVIDIA careers (Workday, site NVIDIAExternalCareerSite).

- Israel filter: facet `locationHierarchy1` = "Israel" (nested inside locationMainGroup).
  Covers Yokneam, Tel Aviv, Raanana, Beer Sheva, Tel Hai and any future Israeli site.
- Unfiltered search is capped at 2000 results and NVIDIA has more, so the filter is mandatory.
- Job type lives in `workerSubType`; in Israel today: Regular Employee / Management / New College Graduate.
  Interns are tagged there too when NVIDIA opens them.
"""
from ..models import Job, SourceError
from . import _workday_http as wd

NAME = "nvidia"
DISPLAY = "NVIDIA"
HOST, TENANT, SITE = "nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"
BASE = wd.base_url(HOST, TENANT, SITE)


def _israel(facets):
    ids = wd.facet_ids(facets, "locationHierarchy1", lambda d: d.strip().lower() == "israel")
    if not ids:
        raise SourceError("NVIDIA: no 'Israel' value in facet locationHierarchy1. Site structure changed?")
    return {"locationHierarchy1": ids}


def _student_subtype(d: str) -> bool:
    d = d.lower()
    return "intern" in d or "student" in d


def _junior_subtype(d: str) -> bool:
    d = d.lower()
    return "new college" in d or "graduate" in d


def fetch_jobs(s) -> list[Job]:
    israel = _israel(wd.search(s, BASE, {}).get("facets", []))
    postings, facets = wd.all_postings(s, BASE, israel)
    junior = wd.tagged_paths(s, BASE, israel, "workerSubType", wd.facet_ids(facets, "workerSubType", _junior_subtype))
    student = wd.tagged_paths(s, BASE, israel, "workerSubType", wd.facet_ids(facets, "workerSubType", _student_subtype))
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
    info = wd.job_detail(s, BASE, job.id)
    return info.get("jobDescription", "")
