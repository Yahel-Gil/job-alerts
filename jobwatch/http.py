import random
import time

import requests

from .models import RateLimited, SourceError

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

# When a site says "slow down" (429/503), wait much longer than for an ordinary glitch.
# Total worst case stays well under the 8-minute job timeout.
SLOW_DOWN = {429, 503}
MAX_WAIT = 90


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": BROWSER_UA, "Accept": "application/json", "Accept-Language": "en-US"})
    return s


def _retry_after(r: requests.Response | None) -> float | None:
    try:
        return float(r.headers["Retry-After"]) if r is not None else None
    except (KeyError, ValueError):
        return None


def get_json(s: requests.Session, method: str, url: str, *, tries: int = 3, **kw) -> dict:
    """Request JSON with a few retries. Some sites occasionally return an empty/HTML body instead of JSON."""
    last, limited = None, False
    for attempt in range(tries):
        r = None
        try:
            r = s.request(method, url, timeout=30, **kw)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            last = e
            limited = r is not None and r.status_code in SLOW_DOWN
            if attempt == tries - 1:
                break
            if limited:
                wait = _retry_after(r) or 15 * 2 ** attempt
                time.sleep(min(wait, MAX_WAIT) + random.uniform(0, 5))
            else:
                time.sleep(2 * (attempt + 1))
    err = RateLimited if limited else SourceError
    raise err(f"{method} {url} failed after {tries} tries: {last}")
