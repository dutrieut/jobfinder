import argparse
import logging
from pathlib import Path

from .adapters import ADAPTERS
from .config import load_config
from .search import JobSearch
from .session import build_session
from .storage import build_store

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--ats", choices=sorted(ADAPTERS))
    parser.add_argument("--company")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    config = load_config(args.config)
    store = build_store(config.storage)
    with build_session(config.http) as session:
        js = JobSearch(
            config=config,
            store=store,
            session=session,
            ats_name=args.ats,
            company_token=args.company,
        )
        jobs = js.search()
        seen = store.seen_ids()
        new_jobs = [job for job in jobs if job.uid not in seen]
        logger.info(
            "%d offer(s) in Paris, including %d new(s)", len(jobs), len(new_jobs)
        )
        store.mark_seen(seen | {job.uid for job in jobs})


if __name__ == "__main__":
    main()
