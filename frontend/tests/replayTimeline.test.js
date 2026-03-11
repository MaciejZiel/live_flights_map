import test from "node:test";
import assert from "node:assert/strict";

import {
  buildReplayCompareSummary,
  findClosestReplaySnapshotIndex,
  getReplayHistoryRequestLimit,
} from "../src/lib/utils/replayTimeline.js";

test("scales replay request limit with larger archive windows", () => {
  assert.equal(getReplayHistoryRequestLimit(30), 120);
  assert.equal(getReplayHistoryRequestLimit(180), 360);
  assert.equal(getReplayHistoryRequestLimit(720), 720);
  assert.equal(getReplayHistoryRequestLimit(1440), 720);
});

test("finds the closest replay snapshot to a target timestamp", () => {
  const snapshots = [
    { fetchedAt: "2026-03-11T10:00:00Z" },
    { fetchedAt: "2026-03-11T10:15:00Z" },
    { fetchedAt: "2026-03-11T10:30:00Z" },
  ];

  assert.equal(findClosestReplaySnapshotIndex(snapshots, "2026-03-11T10:18:00Z"), 1);
  assert.equal(findClosestReplaySnapshotIndex(snapshots, "2026-03-11T10:28:00Z"), 2);
});

test("builds replay comparison summary for arrivals, departures and persisted traffic", () => {
  const summary = buildReplayCompareSummary(
    {
      fetchedAt: "2026-03-11T10:00:00Z",
      count: 3,
      flights: [{ icao24: "aaa111" }, { icao24: "bbb222" }, { icao24: "ccc333" }],
    },
    {
      fetchedAt: "2026-03-11T10:20:00Z",
      count: 4,
      flights: [{ icao24: "bbb222" }, { icao24: "ccc333" }, { icao24: "ddd444" }, { icao24: "eee555" }],
    }
  );

  assert.deepEqual(summary, {
    baseLabel: "2026-03-11T10:00:00Z",
    activeLabel: "2026-03-11T10:20:00Z",
    baseCount: 3,
    activeCount: 4,
    persisted: 2,
    arrivals: 2,
    departures: 1,
    trafficDelta: 1,
  });
});
