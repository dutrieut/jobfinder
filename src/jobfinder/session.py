import tomllib
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .config import _HttpConfig

PYPROJECT = Path(__file__).parent.parent.parent / "pyproject.toml"


def _user_agent() -> str:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    return f"{project['name']}/{project['version']}"


def build_session(config: _HttpConfig) -> requests.Session:
    """Session with retry mechanism (exponential backoff, Retry-After if given)."""
    retry = Retry(
        total=config.retry.number,
        backoff_factor=config.retry.backoff_factor,
        respect_retry_after_header=config.retry.respect_retry_after_header,
        status_forcelist=config.retry.status_forcelist,
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.headers["User-Agent"] = _user_agent()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session
