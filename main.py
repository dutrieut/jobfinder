"""Fetches jobs from ATS public APIs"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import time
import tomllib
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib3.util import Retry

import requests
import yaml
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

TIMEOUT_S = 20
REQUEST_DELAY_S = 0.5
PARIS_RE = re.compile(r"\bparis\b", re.IGNORECASE)
PYPROJECT = Path(__file__).parent / "pyproject.toml"


def user_agent() -> str:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    return f"{project['name']}/{project['version']}"


def parse_date(value: str | int | None) -> datetime | None:
    if value is None:
        return
    if isinstance(value, int):
        dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    else:
        dt = datetime.fromisoformat(value)

    return dt.astimezone(timezone.utc)


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# ATS Adapters
# --------------------------------------------------------------------------- #
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
            job_id=raw["id"],
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


# --------------------------------------------------------------------------- #
# Network requests and configuration
# --------------------------------------------------------------------------- #
def load_targets(
    config_path: Path, ats_name: str | None, company_name: str | None
) -> Iterator[Target]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for entry in config["ats"]:
        for ats, conf in entry.items():
            if ats_name and ats != ats_name:
                continue
            if ats not in ADAPTERS:
                logger.warning("non supported ATS, ignored : %s", ats)
                continue
            for company in conf["companies"]:
                if company_name and company["token"] != company_name:
                    continue
                yield Target(
                    ats=ats,
                    name=company["name"],
                    token=company["token"],
                    endpoint=conf["endpoint"],
                )


def build_session() -> requests.Session:
    """Session with retry mechanism (exponential backoff, Retry-After if given)."""
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers["User-Agent"] = user_agent()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_jobs(session: requests.Session, target: Target) -> list[Job]:
    """Fetch jobs from ATS and filter on Paris."""
    adapter = ADAPTERS[target.ats]
    response = session.get(target.url, params=adapter.params, timeout=TIMEOUT_S)
    response.raise_for_status()
    return [
        job
        for job in adapter.parse(response.json(), target)
        if PARIS_RE.search(job.location)
    ]


def collect_jobs(targets: Iterable[Target], data_dir: Path) -> list[Job]:
    jobs: list[Job] = []
    with build_session() as session:
        for index, target in enumerate(targets):
            if index:
                time.sleep(REQUEST_DELAY_S)
            try:
                found = fetch_jobs(session, target)
            except (requests.RequestException, ValueError, KeyError) as exc:
                logger.warning("%s/%s : failure (%s)", target.ats, target.name, exc)
                continue
            logger.info(
                "%s/%s : %d offer(s) in Paris", target.ats, target.name, len(found)
            )
            write_json(data_dir / target.ats / f"{target.token}.json", [job.to_dict() for job in found])
            jobs.extend(found)
    return jobs


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def json_default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_json(path: Path, data: Any):
    """file is erased if and only if tmp successfully written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8",
    )
    tmp.replace(path)


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")))


def save_seen(path: Path, seen: set[str]):
    write_json(path, sorted(seen))


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--ats", choices=sorted(ADAPTERS))
    parser.add_argument("--company")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    jobs = collect_jobs(
        targets=load_targets(
            config_path=args.config, ats_name=args.ats, company_name=args.company
        ),
        data_dir=args.data_dir,
    )

    seen_path = args.data_dir / "seen.json"
    seen = load_seen(seen_path)
    new_jobs = [job for job in jobs if job.uid not in seen]
    logger.info("%d offer(s) in Paris, including %d new(s)", len(jobs), len(new_jobs))

    # TODO : brancher le LLM ici sur `new_jobs`.

    # Marking as seen after treatment
    save_seen(seen_path, seen | {job.uid for job in jobs})


if __name__ == "__main__":
    main()
