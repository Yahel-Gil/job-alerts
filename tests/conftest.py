import pytest

from jobwatch.sources import _workday_http


@pytest.fixture(autouse=True)
def no_workday_pause(monkeypatch):
    monkeypatch.setattr(_workday_http, "PAUSE", None)
