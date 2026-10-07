from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Target:
    """A company listed on an ATS"""

    ats: str
    name: str
    token: str
    endpoint: str

    @property
    def url(self) -> str:
        return self.endpoint.format(token=self.token)


@dataclass(frozen=True, slots=True)
class Job:
    ats: str
    company: str
    company_token: str
    job_id: str
    title: str
    location: str
    url: str
    published_at: datetime | None
    description: str
    updated_at: datetime | None = None

    @property
    def uid(self) -> str:
        return f"{self.ats}:{self.company_token}:{self.job_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            **asdict(self),
        }