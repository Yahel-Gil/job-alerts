"""End-to-end scan logic with a fake site, fake Telegram and a temp state folder."""
import types

import pytest

from jobwatch import __main__ as app
from jobwatch import ai_score, config, notify, state
from jobwatch.models import Job, SourceError

CFG = config.load()


@pytest.fixture
def env(monkeypatch, tmp_path):
    sent = []
    site = types.SimpleNamespace(NAME="fake", DISPLAY="FakeCorp", jobs=[], error=None)

    def fetch_jobs(s):
        if site.error:
            raise SourceError(site.error)
        return list(site.jobs)

    site.fetch_jobs = fetch_jobs
    site.fetch_description = lambda s, j: "<p>description</p>"
    monkeypatch.setitem(app.SOURCES, "fake", site)
    monkeypatch.setattr(state, "STATE", tmp_path)
    monkeypatch.setattr(ai_score, "score", lambda *a, **k: None)
    monkeypatch.setattr(notify, "send", lambda text, admin=False, dry_run=False: sent.append((text, admin)))
    return site, sent


def J(id_, title):
    return Job(company="fake", id=id_, title=title, locations=["Haifa"], url=f"https://x/{id_}")


def test_first_run_then_only_new_jobs(env):
    site, sent = env
    site.jobs = [J("1", "Hardware Validation Student"), J("2", "Senior Manager")]
    app.scan("fake", CFG, dry_run=False)
    assert len(sent) == 1 and "התחלתי לעקוב" in sent[0][0] and "Hardware Validation Student" in sent[0][0]

    sent.clear()
    app.scan("fake", CFG, dry_run=False)
    assert sent == []  # nothing new

    site.jobs.append(J("3", "ASIC Verification Intern"))
    site.jobs.append(J("4", "Principal Architect"))
    app.scan("fake", CFG, dry_run=False)
    assert len(sent) == 1 and "ASIC Verification Intern" in sent[0][0] and "🟢" in sent[0][0]


def test_closed_jobs_marked_and_digest(env):
    site, sent = env
    site.jobs = [J("1", "Hardware Student"), J("2", "Board Design Student")]
    app.scan("fake", CFG, dry_run=False)
    site.jobs = [J("2", "Board Design Student")]
    app.scan("fake", CFG, dry_run=False)
    seen = state.load("seen", "fake")
    assert seen["1"]["open"] is False and seen["2"]["open"] is True

    sent.clear()
    app.digest({**CFG, "companies": ["fake"]}, dry_run=False)
    assert "Board Design Student" in sent[0][0] and "Hardware Student" not in sent[0][0]


def test_telegram_failure_retries_next_run(env, monkeypatch):
    site, sent = env
    site.jobs = [J("1", "Old Role")]
    app.scan("fake", CFG, dry_run=False)

    def broken(text, admin=False, dry_run=False):
        raise RuntimeError("telegram down")

    monkeypatch.setattr(notify, "send", broken)
    site.jobs.append(J("2", "Silicon Validation Student"))
    app.scan("fake", CFG, dry_run=False)
    assert "2" not in state.load("seen", "fake")

    monkeypatch.setattr(notify, "send", lambda text, admin=False, dry_run=False: sent.append((text, admin)))
    sent.clear()
    app.scan("fake", CFG, dry_run=False)
    assert len(sent) == 1 and "Silicon Validation Student" in sent[0][0]


def test_health_alert_once_then_recovery(env):
    site, sent = env
    site.jobs = [J("1", "Some Role")]
    app.scan("fake", CFG, dry_run=False)
    sent.clear()

    site.error = "structure changed"
    for _ in range(5):
        app.scan("fake", CFG, dry_run=False)
    alerts = [t for t, admin in sent if admin]
    assert len(alerts) == 1 and "FakeCorp" in alerts[0]

    site.error = None
    sent.clear()
    app.scan("fake", CFG, dry_run=False)
    assert any("חזרה לעבוד" in t for t, admin in sent if admin)


def test_ai_score_filters_irrelevant_student(env, monkeypatch):
    site, sent = env
    site.jobs = [J("0", "Old Role")]
    app.scan("fake", CFG, dry_run=False)
    sent.clear()
    fit = ai_score.Fit(score=3, reason_he="לא רלוונטי", is_student_role=True)
    monkeypatch.setattr(ai_score, "score", lambda *a, **k: fit)
    site.jobs.append(J("1", "Data Science Intern"))
    app.scan("fake", CFG, dry_run=False)
    assert sent == []
