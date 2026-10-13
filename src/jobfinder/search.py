import logging
import re
import time
from collections.abc import Iterator

import requests

from .adapters import ADAPTERS
from .config import Config
from .models import Job, Target
from .storage import JobStore

logger = logging.getLogger(__name__)


class JobSearch:
    def __init__(
        self,
        config: Config,
        store: JobStore,
        session: requests.Session,
        ats_name: str | None,
        company_token: str | None,
    ):
        self._config = config
        self._store = store
        self._session = session
        self._ats_name = ats_name
        self._company_token = company_token

    def _get_targets(self) -> Iterator[Target]:
        for ats in self._config.ats:
            if self._ats_name and ats.name != self._ats_name:
                continue
            if ats.name not in ADAPTERS:
                logger.warning("non supported ATS, ignores : %s", ats.name)
                continue
            for company in ats.companies:
                if self._company_token and company.token != self._company_token:
                    continue
                yield Target(
                    ats=ats.name,
                    name=company.name,
                    token=company.token,
                    endpoint=ats.endpoint,
                )

    def _it_jobs_for(self, target: Target) -> Iterator[Job]:
        adapter = ADAPTERS[target.ats]
        response = self._session.get(
            target.url, params=adapter.params, timeout=self._config.http.timeout_s
        )
        response.raise_for_status()
        return adapter.parse(response.json(), target)

    def _filter(self, jobs: Iterator[Job]):
        pattern = re.compile(
            "|".join(
                rf"(?<!\w){re.escape(term)}(?!\w)"
                for term in self._config.search.locations
            ),
            re.IGNORECASE,
        )
        return [job for job in jobs if job.location and pattern.search(job.location)]

    def search(self) -> list[Job]:
        targets = self._get_targets()
        jobs: list[Job] = []
        for index, target in enumerate(targets):
            if index:
                time.sleep(self._config.http.delay_s)
            try:
                _jobs = self._it_jobs_for(target)
                matching = self._filter(_jobs)
            except (requests.RequestException, ValueError, KeyError) as exc:
                logger.warning("%s/%s : failure (%s)", target.ats, target.name, exc)
                continue
            logger.info(
                "%s/%s : %d offer(s) in Paris", target.ats, target.name, len(matching)
            )
            if matching:
                jobs.extend(matching)
                self._store.save(
                    target=target, payload=[job.to_dict() for job in matching]
                )
        return jobs
