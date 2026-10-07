import argparse
import logging
from pathlib import Path

from .adapters import ADAPTERS
from .jobs import collect_jobs, load_targets
from .storage import load_seen, save_seen


logger = logging.getLogger(__name__)


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

    # Marking as seen after treatment
    save_seen(seen_path, seen | {job.uid for job in jobs})


if __name__ == "__main__":
    main()
