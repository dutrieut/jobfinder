import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture() -> Callable[[str], Any]:
    """Load a JSON API response stored under tests/fixtures/."""

    def _load(relative_path: str) -> Any:
        return json.loads((FIXTURES_DIR / relative_path).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def make_session() -> Callable[[Any], MagicMock]:
    """Build a fake requests.Session whose get() returns the given JSON payload."""

    def _make(payload: Any) -> MagicMock:
        session = MagicMock(spec=requests.Session)
        session.get.return_value.json.return_value = payload
        return session

    return _make
