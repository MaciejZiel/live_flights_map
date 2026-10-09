import assert from "node:assert/strict";
import test from "node:test";

import { confirmCachedSnapshot } from "../src/lib/utils/snapshotRevalidation.js";

const HYDRATED_STATE = {
  status: "success",
  flights: [{ icao24: "48af06" }],
  error: null,
  source: "collector_cache",
  warning: "Showing the last locally cached snapshot while live data reconnects.",
  stale: true,
  reason: "local_cache",
  transport: "polling",
  meta: { source: "collector_cache", stale: false, reason: "live" },
};

test("confirmCachedSnapshot drops the local-cache warning when the server confirms the snapshot", () => {
  const next = confirmCachedSnapshot(HYDRATED_STATE, HYDRATED_STATE.meta, "polling");

  assert.equal(next.warning, null);
  assert.equal(next.stale, false);
  assert.equal(next.reason, "live");
  assert.equal(next.source, "collector_cache");
  assert.equal(next.status, "success");
  assert.deepEqual(next.flights, HYDRATED_STATE.flights);
});

test("confirmCachedSnapshot keeps server-side staleness from the cached meta", () => {
  const meta = { source: "collector_cache", stale: true, reason: "provider_cooldown", warning: "Delayed." };
  const next = confirmCachedSnapshot(HYDRATED_STATE, meta, "polling");

  assert.equal(next.warning, "Delayed.");
  assert.equal(next.stale, true);
  assert.equal(next.reason, "provider_cooldown");
});

test("confirmCachedSnapshot tolerates a missing meta object", () => {
  const next = confirmCachedSnapshot({ ...HYDRATED_STATE, error: "boom" }, null, "sse");

  assert.equal(next.error, null);
  assert.equal(next.warning, null);
  assert.equal(next.reason, "live");
  assert.equal(next.transport, "sse");
});
