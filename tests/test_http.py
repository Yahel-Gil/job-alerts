import pytest
import requests

from jobwatch import http
from jobwatch.models import RateLimited, SourceError


class Resp:
    def __init__(self, status, headers=None, body=None):
        self.status_code, self.headers, self._body = status, headers or {}, body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)

    def request(self, *a, **k):
        return self.responses.pop(0)


@pytest.fixture
def waits(monkeypatch):
    w = []
    monkeypatch.setattr(http.time, "sleep", w.append)
    monkeypatch.setattr(http.random, "uniform", lambda a, b: 0)
    return w


def test_429_waits_longer_and_honors_retry_after(waits):
    s = FakeSession([Resp(429), Resp(429, {"Retry-After": "40"}), Resp(200, body={"ok": 1})])
    assert http.get_json(s, "GET", "https://x") == {"ok": 1}
    assert waits == [15, 40]


def test_persistent_429_raises_rate_limited(waits):
    with pytest.raises(RateLimited):
        http.get_json(FakeSession([Resp(429)] * 3), "GET", "https://x")
    assert waits == [15, 30]  # no pointless sleep after the last try


def test_other_errors_stay_quick_and_plain(waits):
    with pytest.raises(SourceError) as e:
        http.get_json(FakeSession([Resp(500)] * 3), "GET", "https://x")
    assert not isinstance(e.value, RateLimited) and waits == [2, 4]
