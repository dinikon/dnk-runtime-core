"""Standard-library-only probes of state published by the scheduled-job worker."""

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path


def fresh(path: Path, max_age: float = 30) -> bool:
    try:
        timestamp = datetime.fromisoformat(path.read_text().strip())
        age = (datetime.now(UTC) - timestamp).total_seconds()
        return 0 <= age <= max_age
    except (OSError, ValueError, TypeError):
        return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--liveness", action="store_true")
    args = parser.parse_args(argv)
    heartbeat = Path(
        os.environ.get(
            "SCHEDULED_JOBS__HEARTBEAT_PATH", "/tmp/dnk-cron-worker-heartbeat"
        )
    )
    if not fresh(heartbeat):
        return 1
    # Readiness is refreshed only after a successful DB operation. DB downtime
    # makes the pod unready without restarting a responsive worker.
    return 0 if args.liveness or fresh(Path(str(heartbeat) + ".ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
