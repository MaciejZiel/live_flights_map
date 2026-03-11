from __future__ import annotations

import argparse
import json
import time

from dotenv import load_dotenv

from backend.runtime import build_runtime

DEFAULT_INTERVAL_SECONDS = 30.0


def _run_loop(*, once: bool, interval_seconds: float) -> None:
    runtime = build_runtime()
    while True:
        payload = runtime.alert_sweep_service.run_once()
        print(json.dumps(payload, ensure_ascii=True), flush=True)
        if once:
            return
        time.sleep(interval_seconds)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Scan synced workspace alert rules against live traffic.")
    parser.add_argument("--once", action="store_true", help="Run one alert sweep and exit.")
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Polling interval in seconds when running continuously (default: {DEFAULT_INTERVAL_SECONDS}).",
    )
    args = parser.parse_args()
    _run_loop(once=args.once, interval_seconds=max(args.interval, 5.0))


if __name__ == "__main__":
    main()
