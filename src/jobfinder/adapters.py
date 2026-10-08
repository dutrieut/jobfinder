import html
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from .models import Job, Target


def parse_date(value: str | int | None) -> datetime | None:
    if value is None:
        return
    if isinstance(value, int):
        dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    else:
        dt = datetime.fromisoformat(value)

    return dt.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class Adapter:
    parse: Callable[[Any, Target], Iterator[Job]]
    params: dict[str, str] = field(default_factory=dict)


ADAPTERS: dict[str, Adapter] = {}


def register(ats: str, params: dict[str, str] | None = None):
    """Registers ATS parsing function"""

    def decorator(func: Callable[[Any, Target], Iterator[Job]]):
        ADAPTERS[ats] = Adapter(parse=func, params=params or {})
        return func

    return decorator


def html_to_text(raw: str | None, unescape: bool = False) -> str:
    if raw is None:
        return ""
    if unescape:
        raw = html.unescape(raw)
    return (
        BeautifulSoup(raw, "html.parser")
        .get_text("\n", strip=True)
        .replace("\xa0", " ")
    )


@register("greenhouse", params={"content": "true"})
def parse_greenhouse(payload: Any, target: Target) -> Iterator[Job]:
    for raw in payload.get("jobs", []):
        yield Job(
            ats=target.ats,
            company=target.name,
            company_token=target.token,
            job_id=str(raw["id"]),
            title=raw.get("title"),
            location=raw.get("location", {}).get("name"),
            url=raw.get("absolute_url"),
            published_at=parse_date(raw.get("first_published")),
            updated_at=parse_date(raw.get("updated_at")),
            description=html_to_text(raw.get("content"), unescape=True) or None,
        )


@register("ashbyhq")
def parse_ashbyhq(payload: Any, target: Target) -> Iterator[Job]:
    for raw in payload.get("jobs", []):
        location = raw["location"]
        for secondary_location in raw.get("secondaryLocations", []):
            location += f",{secondary_location['location']}"
        yield Job(
            ats=target.ats,
            company=target.name,
            company_token=target.token,
            job_id=raw["id"],
            title=raw.get("title"),
            location=location,
            url=raw.get("jobUrl"),
            published_at=parse_date(raw.get("publishedAt")),
            description=raw.get("descriptionPlain")
            or html_to_text(raw.get("descriptionHtml"))
            or None,
        )


@register("lever", params={"mode": "json"})
def parse_lever(payload: Any, target: Target) -> Iterator[Job]:
    for raw in payload:
        additional_content = [
            f"{item.get('text', '')}\n{html_to_text(item.get('content'))}"
            for item in raw.get("lists", [])
        ]
        parts = [
            raw.get("openingPlain") or html_to_text(raw.get("opening")),
            raw.get("descriptionPlain") or html_to_text(raw.get("description")),
            raw.get("descriptionBodyPlain") or html_to_text(raw.get("descriptionBody")),
            *additional_content,
            raw.get("additionalPlain") or html_to_text(raw.get("additional")),
        ]
        description = "\n".join(part for part in parts if part)
        yield Job(
            ats=target.ats,
            company=target.name,
            company_token=target.token,
            job_id=raw["id"],
            title=raw.get("text", ""),
            location=",".join(raw.get("categories", {}).get("allLocations", [])),
            url=raw.get("hostedUrl"),
            published_at=parse_date(raw.get("createdAt")),
            description=description,
        )
