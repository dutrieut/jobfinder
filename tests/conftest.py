import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests
import yaml

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------
# Config testing responses
# ---------------------------------------------------------------------
@pytest.fixture
def valid_config_data():
    return {
        "ats": [
            {
                "name": "greenhouse",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                "companies": [
                    {"name": "A-TEK", "token": "atek"},
                    {"name": "Acme", "token": "acme"},
                ],
            }
        ],
        "http": {
            "timeout_s": 20,
            "delay_s": 0.5,
            "retry": {
                "number": 5,
                "backoff_factor": 1.0,
                "respect_retry_after_header": True,
                "status_forcelist": [429, 500, 502, 503, 504],
            },
        },
        "search": {
            "locations": ["Paris", "London"],
        },
        "storage": {
            "type": "json",
            "data_dir": "data",
        },
    }


@pytest.fixture
def config_file(tmp_path, valid_config_data):
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(valid_config_data),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------
# API response fixtures
# ---------------------------------------------------------------------
@pytest.fixture
def load_fixture() -> Callable[[str], Any]:
    """Load a JSON API response stored under tests/fixtures/responses/."""

    def _load(relative_path: str) -> Any:
        return json.loads(
            (FIXTURES_DIR / "responses" / relative_path).read_text(encoding="utf-8")
        )

    return _load


@pytest.fixture
def make_session() -> Callable[[Any], MagicMock]:
    """Build a fake requests.Session whose get() returns the given JSON payload."""

    def _make(payload: Any) -> MagicMock:
        session = MagicMock(spec=requests.Session)
        session.get.return_value.json.return_value = payload
        return session

    return _make
