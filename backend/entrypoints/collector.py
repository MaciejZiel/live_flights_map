from __future__ import annotations

import argparse
import json
import os
import time

from dotenv import load_dotenv

from backend.runtime import build_runtime

MIN_RETRY_DELAY_SECONDS = 30.0
FAILURE_RETRY_DELAY_SECONDS = 60.0


def _default_interval_seconds() -> float:
    configured = os.getenv("SNAPSHOT_COLLECTOR_INTERVAL_SECONDS", "").strip()
    if configured:
        return float(configured)
    if os.getenv("OPENSKY_CLIENT_ID") and os.getenv("OPENSKY_CLIENT_SECRET"):
        return 180.0
    return 1200.0


def _next_delay_seconds(payload: dict, interval_seconds: float) -> float:
    if not payload.get("warnings"):
        return interval_seconds

    retry_after_seconds = max(
        (float(sector.get("retry_after_seconds") or 0) for sector in payload.get("sectors", [])),
        default=0.0,
    )
    if retry_after_seconds > 0:
        return max(MIN_RETRY_DELAY_SECONDS, retry_after_seconds)
    return min(interval_seconds, FAILURE_RETRY_DELAY_SECONDS)


def _run_loop(*, once: bool, interval_seconds: float) -> None:
    runtime = build_runtime()
    while True:
        payload = runtime.snapshot_collector_service.collect_once()
        print(json.dumps(payload, ensure_ascii=True), flush=True)
        if once:
            return
        time.sleep(_next_delay_seconds(payload, interval_seconds))


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Warm the live snapshot cache and archive sectors continuously.")
    parser.add_argument("--once", action="store_true", help="Collect one pass and exit.")
    parser.add_argument(
        "--interval",
        type=float,
        default=_default_interval_seconds(),
        help="Polling interval in seconds when running continuously.",
    )
    args = parser.parse_args()
    _run_loop(once=args.once, interval_seconds=max(args.interval, 5.0))


if __name__ == "__main__":
    main()
