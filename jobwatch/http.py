import time

import requests

from .models import SourceError

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": BROWSER_UA, "Accept": "application/json", "Accept-Language": "en-US"})
    return s


def get_json(s: requests.Session, method: str, url: str, *, tries: int = 3, **kw) -> dict:
    """Request JSON with a few retries. Some sites occasionally return an empty/HTML body instead of JSON."""
    last = None
    for attempt in range(tries):
        try:
            r = s.request(method, url, timeout=30, **kw)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise SourceError(f"{method} {url} failed after {tries} tries: {last}")
