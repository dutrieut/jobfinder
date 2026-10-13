from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from jobfinder.models import Target


class JobStore(Protocol):
    def save(self, target: Target, payload: Any):
        """Store the Job from API response for a target, replacing any previous one."""
        pass

    def load(self, target: Target):
        """Return the stored Job for a target, or None if there is none."""
        pass

    def seen_ids(self) -> set[str]:
        """Return the uids of all jobs already processed."""
        pass

    def mark_seen(self, uids: Iterable[str]):
        """Add uids to the set of already-processed jobs."""
        pass
