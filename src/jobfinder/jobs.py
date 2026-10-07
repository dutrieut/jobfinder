import logging
import re
import time
import tomllib
from collections.abc import Iterator, Iterable
from pathlib import Path
from urllib3.util import Retry

import requests
import yaml
from requests.adapters import HTTPAdapter

from .adapters import ADAPTERS
from .models import Job, Target
from .storage import write_json


TIMEOUT_S = 20
REQUEST_DELAY_S = 0.5
PARIS_RE = re.compile(r"\bparis\b", re.IGNORECASE)
PYPROJECT = Path(__file__).parent.parent.parent / "pyproject.toml"

logger = logging.getLogger(__name__)


def user_agent() -> str:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    return f"{project['name']}/{project['version']}"


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