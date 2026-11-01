"""Record real site responses once, replay them in tests.

    .venv/bin/python -m tests.recorder        # re-record every site's fixtures from the live sites
"""
import hashlib
import json
from pathlib import Path

from jobwatch import http
from jobwatch.sources import SOURCES, _workday_http, apple, microsoft

FIXTURES = Path(__file__).parent / "fixtures"
PATCH_POINTS = (_workday_http, apple, microsoft)  # modules that imported get_json by name


def _key(method: str, url: str, kw: dict) -> str:
    raw = json.dumps([method, url, kw.get("json"), kw.get("params")], sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def replay(monkeypatch, company: str) -> None:
    folder = FIXTURES / company

    def fake(s, method, url, **kw):
        path = folder / f"{_key(method, url, kw)}.json"
        if not path.exists():
            raise AssertionError(f"no fixture for {method} {url} {kw}. Re-record with: python -m tests.recorder")
        return json.loads(path.read_text(encoding="utf-8"))

    for m in PATCH_POINTS:
        monkeypatch.setattr(m, "get_json", fake)


def record() -> None:
    real = http.get_json
    for name, src in SOURCES.items():
        folder = FIXTURES / name
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.json"):
            old.unlink()

        def rec(s, method, url, _folder=folder, **kw):
            data = real(s, method, url, **kw)
            (_folder / f"{_key(method, url, kw)}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data

        for m in PATCH_POINTS:
            m.get_json = rec
        s = http.session()
        jobs = src.fetch_jobs(s)
        src.fetch_description(s, jobs[0])
        print(f"{name}: recorded {len(list(folder.glob('*.json')))} responses, {len(jobs)} jobs")
    for m in PATCH_POINTS:
        m.get_json = real


if __name__ == "__main__":
    record()
