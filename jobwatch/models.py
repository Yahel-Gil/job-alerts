from dataclasses import dataclass, field


class SourceError(Exception):
    """A career site answered in a way we don't understand (down, blocked, or changed structure)."""


@dataclass
class Job:
    company: str
    id: str
    title: str
    locations: list[str]
    url: str
    posted: str | None = None      # ISO date when the site gives one, otherwise the site's own text
    tier_hint: str | None = None   # "student" / "junior" when the site marks it in a structured field
    team: str | None = None
    extra: dict = field(default_factory=dict)  # whatever the source needs later to fetch the description
