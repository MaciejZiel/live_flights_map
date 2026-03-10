from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic


class DiagnosticsService:
    def __init__(self, snapshot_service, archive_service, workspace_service) -> None:
        self.snapshot_service = snapshot_service
        self.archive_service = archive_service
        self.workspace_service = workspace_service

    def build_healthcheck(self) -> dict[str, object]:
        warnings = []
        live_snapshot = self._build_snapshot_diagnostics()
        archive = self._summarize_archive()
        workspace = self._summarize_workspace()

        if live_snapshot["active_cooldowns"]:
            warnings.append("Some live data providers are cooling down.")
        if not archive["available"]:
            warnings.append("Flight archive database is unavailable.")
        if not workspace["available"]:
            warnings.append("Workspace database is unavailable.")

        return {
            "status": "degraded" if warnings else "ok",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "warnings": warnings,
            "services": {
                "live_snapshot": live_snapshot,
                "archive": archive,
                "workspace": workspace,
            },
        }

    def _build_snapshot_diagnostics(self) -> dict[str, object]:
        snapshot_service = self.snapshot_service
        cache_path = getattr(snapshot_service, "_cache_path", None)
        now = monotonic()

        with snapshot_service._lock:
            cache_entries = len(getattr(snapshot_service, "_cache", {}))
            active_cooldowns = snapshot_service._active_cooldowns(now)

        return {
            "provider_count": len(snapshot_service.providers),
            "providers": [provider.name for provider in snapshot_service.providers],
            "cache_entries": cache_entries,
            "cache_ttl_seconds": snapshot_service.cache_ttl,
            "cooldown_seconds": snapshot_service.cooldown_seconds,
            "active_cooldowns": active_cooldowns,
            "cache_path": str(cache_path) if cache_path else None,
            "cache_file_present": bool(cache_path and Path(cache_path).exists()),
        }

    def _summarize_archive(self) -> dict[str, object]:
        return self._summarize_sqlite(
            path=self.archive_service.archive_path,
            count_queries={
                "snapshot_rows": "SELECT COUNT(*) FROM snapshots",
                "position_rows": "SELECT COUNT(*) FROM positions",
            },
            extra_queries={
                "latest_snapshot_at": "SELECT MAX(fetched_at) FROM snapshots",
            },
            extra_payload={
                "retention_hours": self.archive_service.retention_hours,
                "max_snapshots": self.archive_service.max_snapshots,
            },
        )

    def _summarize_workspace(self) -> dict[str, object]:
        return self._summarize_sqlite(
            path=self.workspace_service.workspace_path,
            count_queries={
                "account_rows": "SELECT COUNT(*) FROM accounts",
                "profile_rows": "SELECT COUNT(*) FROM profiles",
                "state_rows": "SELECT COUNT(*) FROM workspace_state",
            },
            extra_queries={
                "latest_profile_update_at": "SELECT MAX(updated_at) FROM profiles",
            },
        )

    @staticmethod
    def _summarize_sqlite(
        path: Path,
        count_queries: dict[str, str],
        extra_queries: dict[str, str] | None = None,
        extra_payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        payload = {
            "path": str(path),
            "available": False,
            "file_present": path.exists(),
            **(extra_payload or {}),
        }

        if not path.exists():
            return payload

        try:
            with closing(sqlite3.connect(path)) as connection:
                for key, query in count_queries.items():
                    payload[key] = connection.execute(query).fetchone()[0]
                for key, query in (extra_queries or {}).items():
                    payload[key] = connection.execute(query).fetchone()[0]
        except sqlite3.Error as exc:
            payload["error"] = str(exc)
            return payload

        payload["available"] = True
        return payload
