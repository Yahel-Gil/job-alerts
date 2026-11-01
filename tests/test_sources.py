"""Each scraper against real responses recorded on 2026-11-01."""
import pytest

from jobwatch.models import SourceError
from jobwatch.sources import _workday_http as wd
from jobwatch.sources import amat, apple, intel, microsoft, nvidia

from .recorder import replay


def _common(jobs, url_prefix):
    assert jobs
    assert len({j.id for j in jobs}) == len(jobs)
    assert all(j.url.startswith(url_prefix) for j in jobs)
    assert all(j.title for j in jobs)


def test_nvidia(monkeypatch):
    replay(monkeypatch, "nvidia")
    jobs = nvidia.fetch_jobs(None)
    _common(jobs, "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/")
    assert len(jobs) == 421  # all Israel, well below Workday's 2000 cap
    assert all("Israel" in j.locations[0] or "Locations" in j.locations[0] for j in jobs)
    juniors = {j.title for j in jobs if j.tier_hint == "junior"}
    assert "Physical Design Backend Engineer" in juniors  # tagged "New College Graduate" by NVIDIA
    assert "<" in nvidia.fetch_description(None, jobs[0])  # HTML description


def test_intel_students_from_structured_facets(monkeypatch):
    replay(monkeypatch, "intel")
    jobs = intel.fetch_jobs(None)
    _common(jobs, "https://intel.wd1.myworkdayjobs.com/External/job/")
    assert all(j.locations[0].startswith("Israel") or "Locations" in j.locations[0] for j in jobs)
    students = {j.title for j in jobs if j.tier_hint == "student"}
    assert {"Haifa Lab technician - Student", "Software Development student"} <= students


def test_amat(monkeypatch):
    replay(monkeypatch, "amat")
    jobs = amat.fetch_jobs(None)
    _common(jobs, "https://amat.wd1.myworkdayjobs.com/External/job/")
    assert len(jobs) == 79
    assert not any("ISR" in j.locations[0] for j in jobs)  # ",ISR" suffix stripped


def test_apple_merges_cities(monkeypatch):
    replay(monkeypatch, "apple")
    jobs = apple.fetch_jobs(None)
    _common(jobs, "https://jobs.apple.com/en-il/details/")
    hw = next(j for j in jobs if j.title == "Hardware Engineering Student")
    assert sorted(hw.locations) == ["Haifa", "Herzliya", "Jerusalem"]
    assert hw.team and hw.posted and len(hw.posted) == 10
    assert apple.fetch_description(None, jobs[0])


def test_microsoft_israel_only(monkeypatch):
    replay(monkeypatch, "microsoft")
    jobs = microsoft.fetch_jobs(None)
    _common(jobs, "https://apply.careers.microsoft.com/careers/job/")
    assert len(jobs) == 26
    assert any("INTERN" in j.title.upper() for j in jobs)
    assert microsoft.fetch_description(None, jobs[0])


def test_workday_nested_facets_and_missing_israel():
    facets = [{"facetParameter": "locationMainGroup", "values": [
        {"facetParameter": "locationHierarchy1", "values": [{"descriptor": "Israel", "id": "IL"}, {"descriptor": "India", "id": "IN"}]},
    ]}]
    assert wd.facet_ids(facets, "locationHierarchy1", lambda d: d == "Israel") == ["IL"]
    with pytest.raises(SourceError):
        nvidia._israel([])


def test_workday_refuses_unfiltered_results(monkeypatch):
    monkeypatch.setattr(wd, "get_json", lambda *a, **k: {"total": 2000, "jobPostings": [], "facets": []})
    with pytest.raises(SourceError):
        wd.all_postings(None, "https://x", {})
