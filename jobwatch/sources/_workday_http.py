"""HTTP plumbing shared by the three Workday sites (NVIDIA, Intel, Applied Materials).

Only the transport lives here. Which facet means "Israel", which facet marks a student,
and how a posting becomes a Job is decided separately in each company's module.
"""
from ..http import get_json
from ..models import SourceError

PAGE = 20  # Workday refuses larger pages


def base_url(host: str, tenant: str, site: str) -> str:
    return f"https://{host}/wday/cxs/{tenant}/{site}"


def search(s, base: str, applied_facets: dict, offset: int = 0) -> dict:
    body = {"appliedFacets": applied_facets, "limit": PAGE, "offset": offset, "searchText": ""}
    return get_json(s, "POST", f"{base}/jobs", json=body)


def all_postings(s, base: str, applied_facets: dict) -> tuple[list[dict], list[dict]]:
    """Every posting matching the facets, plus the facet counts for that filtered set.
    Workday only reports `total` reliably on the first page."""
    first = search(s, base, applied_facets)
    total = first.get("total", 0)
    if total >= 2000:
        raise SourceError(f"{base}: {total} results means the Israel filter was not applied")
    postings = list(first.get("jobPostings", []))
    while len(postings) < total:
        page = search(s, base, applied_facets, offset=len(postings)).get("jobPostings", [])
        if not page:
            break
        postings.extend(page)
    # Workday occasionally returns a stub posting without a path (seen once at NVIDIA); it has no page to link to.
    return [p for p in postings if p.get("externalPath")], first.get("facets", [])


def tagged_paths(s, base: str, israel: dict, param: str, ids: list[str]) -> set[str]:
    """externalPaths of Israel postings that also carry one of the given facet values."""
    if not ids:
        return set()
    postings, _ = all_postings(s, base, {**israel, param: ids})
    return {p["externalPath"] for p in postings}


def iter_facet_values(facets: list[dict]):
    """Yield (facetParameter, value) for every facet value, including ones nested under group facets
    (e.g. NVIDIA's locationHierarchy1 lives inside locationMainGroup)."""
    for f in facets:
        param = f.get("facetParameter")
        for v in f.get("values", []):
            if "values" in v and "facetParameter" in v:
                yield from iter_facet_values([v])
            else:
                yield param, v


def facet_ids(facets: list[dict], param: str, match) -> list[str]:
    return [v["id"] for p, v in iter_facet_values(facets) if p == param and match(v.get("descriptor", ""))]


def job_detail(s, base: str, external_path: str) -> dict:
    return get_json(s, "GET", f"{base}{external_path}").get("jobPostingInfo", {})
