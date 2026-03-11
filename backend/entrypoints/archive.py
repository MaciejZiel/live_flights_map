from __future__ import annotations

import argparse
import json
import time

from dotenv import load_dotenv

from backend.runtime import build_runtime

DEFAULT_INTERVAL_SECONDS = 300.0


def _run_loop(*, once: bool, interval_seconds: float, vacuum: bool) -> None:
    runtime = build_runtime()
    while True:
        payload = runtime.flight_archive_service.run_maintenance(vacuum=vacuum)
        print(json.dumps(payload, ensure_ascii=True), flush=True)
        if once:
            return
        time.sleep(interval_seconds)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Prune and compact the local flight archive.")
    parser.add_argument("--once", action="store_true", help="Run archive maintenance once and exit.")
    parser.add_argument("--vacuum", action="store_true", help="Run SQLite VACUUM after pruning.")
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Maintenance interval in seconds when running continuously (default: {DEFAULT_INTERVAL_SECONDS}).",
    )
    args = parser.parse_args()
    _run_loop(
        once=args.once,
        interval_seconds=max(args.interval, 30.0),
        vacuum=args.vacuum,
    )


if __name__ == "__main__":
    main()
