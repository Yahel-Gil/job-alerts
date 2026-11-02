import pytest

from jobwatch import config, filters
from jobwatch.models import Job

CFG = config.load()


def job(title, hint=None, team=None):
    return Job(company="x", id=title, title=title, locations=["Haifa"], url="https://x", tier_hint=hint, team=team)


@pytest.mark.parametrize("title,hint,expected", [
    ("Hardware Validation Student", None, "student"),
    ("Silicon Design Intern", None, "student"),
    ("Data Science Internship Opportunities", None, "student"),
    ("Applied Sciences INTERN", None, "student"),
    ("סטודנט/ית לולידציה", None, "student"),
    ("Internal Audit Manager", None, None),            # "intern" inside a word
    ("International Sales Lead", None, None),
    ("Junior Verification Engineer", None, "junior"),
    ("New Grad ASIC Engineer", None, "junior"),
    ("Senior Graduate Program Manager", None, None),   # senior wins over graduate
    ("Firmware Engineer", "junior", "junior"),         # structured site flag
    ("Senior Firmware Engineer", "junior", None),
    ("Lab technician", "student", "student"),
    ("Senior Physical Design Engineer", None, None),
])
def test_tier(title, hint, expected):
    assert filters.tier(job(title, hint), CFG) == expected


def test_domain_hits_use_word_edges():
    assert "rf" in filters.domain_hits(job("RF Validation Student"), CFG)
    assert "rf" not in filters.domain_hits(job("Performance Student"), CFG)
    assert filters.domain_hits(job("Engineering Student", team="Hardware"), CFG) == ["hardware"]
    assert filters.domain_hits(job("Data Science Intern"), CFG) == []


@pytest.mark.parametrize("hour,quiet", [(21, False), (22, True), (2, True), (6, True), (7, False), (13, False)])
def test_quiet_hours(hour, quiet):
    from datetime import datetime

    from jobwatch import notify
    assert notify.is_quiet_hours(datetime(2026, 11, 2, hour, 30)) is quiet


@pytest.mark.parametrize("tier,hits,score,expected", [
    ("student", ["asic"], None, True),
    ("student", ["asic"], 4, True),     # keyword match needs only a low bar
    ("student", ["hw"], 2, False),      # ...but a clear misfit (e.g. PhD-only research) is dropped
    ("student", [], None, True),        # AI unavailable: don't risk missing it
    ("student", [], 5, False),
    ("student", [], 6, True),
    ("junior", ["asic"], None, True),
    ("junior", ["asic"], 6, False),
    ("junior", ["asic"], 7, True),
    ("junior", [], 10, False),
    (None, ["asic"], 10, False),
])
def test_should_send(tier, hits, score, expected):
    assert filters.should_send(tier, hits, score, CFG) is expected
