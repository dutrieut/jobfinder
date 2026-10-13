"""JSON-files implementation of the JobStore interface.

Layout:
    <root>/<ats>/<token>.json   raw API response of one company
    <root>/seen.json                sorted list of already-seen job uids
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jobfinder.models import Target


def _check_path_component(value: str) -> str:
    """Reject values that could escape the storage directory (e.g. '../x')."""
    if value in {"", ".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"Unsafe path component: {value!r}")
    return value


def _json_default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _write_json_atomic(path: Path, data: Any) -> None:
    """Write to a tmp file, then rename: a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    tmp.replace(path)


class JsonStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @property
    def _seen_path(self) -> Path:
        return self.root / "seen.json"

    def _store_path(self, target: Target) -> Path:
        return (
            self.root
            / _check_path_component(target.ats)
            / f"{_check_path_component(target.token)}.json"
        )

    def save(self, target: Target, payload: Any) -> None:
        _write_json_atomic(self._store_path(target), payload)

    def load(self, target: Target) -> Any | None:
        path = self._store_path(target)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def seen_ids(self) -> set[str]:
        if not self._seen_path.exists():
            return set()
        return set(json.loads(self._seen_path.read_text(encoding="utf-8")))

    def mark_seen(self, uids: Iterable[str]) -> None:
        _write_json_atomic(self._seen_path, sorted(self.seen_ids() | set(uids)))
