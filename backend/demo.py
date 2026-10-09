"""Demo-mode wiring: synthetic snapshot collection and public-deployment guards."""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .services.demo_traffic import SyntheticTrafficProvider

logger = logging.getLogger(__name__)

WORLD_BBOX = {"lamin": -90.0, "lamax": 90.0, "lomin": -180.0, "lomax": 180.0}
READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# Each open SSE connection pins a server thread; the demo image polls instead.
DEMO_DISABLED_PATHS = frozenset({"/api/flights/stream"})


class SlidingWindowRateLimiter:
    """In-memory per-client limiter: at most ``limit`` requests per ``window`` seconds."""

    def __init__(self, limit: int, window_seconds: float = 60.0, clock=time.monotonic, max_clients: int = 10000) -> None:
        self.limit = max(int(limit), 1)
        self.window_seconds = float(window_seconds)
        self.max_clients = max_clients
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """Record a request; return (allowed, seconds until the next one is allowed)."""
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= self.max_clients:
                    self._evict(cutoff)
                hits = self._hits[key] = deque()
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, math.ceil(hits[0] + self.window_seconds - now))
                return False, retry_after
            hits.append(now)
            return True, 0

    def _evict(self, cutoff: float) -> None:
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in stale:
            del self._hits[key]
        if len(self._hits) >= self.max_clients:
            self._hits.clear()


def _client_key(trust_proxy_headers: bool) -> str:
    if trust_proxy_headers:
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        first_hop = forwarded_for.split(",")[0].strip()
        if first_hop:
            return first_hop
    return request.remote_addr or "unknown"


def install_demo_guards(app: Flask) -> None:
    """Make the API read-only and rate limited for a public demo deployment."""
    limiter = SlidingWindowRateLimiter(app.config.get("DEMO_RATE_LIMIT_PER_MINUTE", 240))
    global_limiter = SlidingWindowRateLimiter(app.config.get("DEMO_GLOBAL_RATE_LIMIT_PER_MINUTE", 3000))
    trust_proxy_headers = bool(app.config.get("DEMO_TRUST_PROXY_HEADERS"))
    app.extensions["demo_rate_limiter"] = limiter

    @app.before_request
    def enforce_demo_guards():
        if not request.path.startswith("/api/"):
            return None
        if request.method not in READ_ONLY_METHODS:
            return jsonify({"error": "This public demo is read-only.", "demo": True}), 403
        if request.path in DEMO_DISABLED_PATHS:
            return jsonify({"error": "The live stream is disabled in demo mode; use polling.", "demo": True}), 404
        allowed, retry_after = limiter.check(_client_key(trust_proxy_headers))
        if allowed:
            allowed, retry_after = global_limiter.check("*")
        if not allowed:
            response = jsonify({"error": "Too many requests to the demo. Try again shortly.", "demo": True})
            response.status_code = 429
            response.headers["Retry-After"] = str(retry_after)
            return response
        return None

    @app.after_request
    def mark_demo_response(response):
        response.headers["X-Demo-Mode"] = "synthetic"
        return response


def install_frontend(app: Flask, dist_path: str) -> None:
    """Serve the built single-page app from Flask (single-container deployments)."""
    root = Path(dist_path).resolve()
    if not (root / "index.html").is_file():
        logger.warning("FRONTEND_DIST_PATH %s has no index.html; not serving the frontend.", root)
        return

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path: str):
        if path.startswith("api/"):
            return jsonify({"error": "Not found."}), 404
        candidate = (root / path).resolve()
        if path and candidate.is_file() and root in candidate.parents:
            response = send_from_directory(root, path)
            if path.startswith("assets/"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return response
        response = send_from_directory(root, "index.html")
        response.headers["Cache-Control"] = "no-cache"
        return response


class DemoSnapshotCollector:
    """Keeps the archive filled with synthetic snapshots so live view and replay work."""

    def __init__(self, runtime, provider: SyntheticTrafficProvider, interval_seconds: float, backfill_minutes: float) -> None:
        self.runtime = runtime
        self.provider = provider
        self.interval_seconds = max(float(interval_seconds), 5.0)
        self.backfill_minutes = max(float(backfill_minutes), 0.0)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def backfill(self, now: float | None = None) -> int:
        """Store synthetic snapshots for the recent past so replay has history at once."""
        now = time.time() if now is None else now
        archive = self.runtime.flight_archive_service
        steps = int(self.backfill_minutes * 60 // self.interval_seconds)
        stored = 0
        for step in range(steps, 0, -1):
            archive.store_snapshot(self.provider.snapshot_at(now - step * self.interval_seconds, WORLD_BBOX))
            stored += 1
        return stored

    def collect_once(self) -> dict[str, object]:
        return self.runtime.snapshot_collector_service.collect_once()

    def run(self) -> None:
        try:
            stored = self.backfill()
            logger.info("Demo mode: backfilled %s synthetic snapshots.", stored)
        except Exception:
            logger.exception("Demo mode: backfill failed.")
        while not self._stop.is_set():
            try:
                self.collect_once()
            except Exception:
                logger.exception("Demo mode: snapshot collection failed.")
            self._stop.wait(self.interval_seconds)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self.run, name="demo-snapshot-collector", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
