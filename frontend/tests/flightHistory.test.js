import assert from "node:assert/strict";
import test from "node:test";

import { getTrailPoints, updateFlightHistory } from "../src/lib/utils/flightHistory.js";

test("updateFlightHistory deduplicates identical positions", () => {
  const fetchedAt = "2026-03-10T12:00:00.000Z";
  const history = updateFlightHistory(new Map(), [
    {
      icao24: "abc123",
      latitude: 52.1,
      longitude: 21.0,
      altitude: 1000,
      velocity: 200,
      vertical_rate: 0,
    },
  ], fetchedAt);

  const deduplicated = updateFlightHistory(history, [
    {
      icao24: "abc123",
      latitude: 52.1,
      longitude: 21.0,
      altitude: 1100,
      velocity: 220,
      vertical_rate: 1,
    },
  ], "2026-03-10T12:00:30.000Z");

  assert.equal(getTrailPoints(deduplicated, "abc123").length, 1);
});

test("updateFlightHistory trims points older than retention window", () => {
  const initial = updateFlightHistory(new Map(), [
    {
      icao24: "abc123",
      latitude: 52.1,
      longitude: 21.0,
      altitude: 1000,
      velocity: 200,
      vertical_rate: 0,
    },
  ], "2026-03-10T12:00:00.000Z");

  const trimmed = updateFlightHistory(initial, [
    {
      icao24: "abc123",
      latitude: 52.2,
      longitude: 21.1,
      altitude: 1500,
      velocity: 210,
      vertical_rate: 2,
    },
  ], "2026-03-10T12:06:00.000Z");

  const points = getTrailPoints(trimmed, "abc123");
  assert.equal(points.length, 1);
  assert.equal(points[0].latitude, 52.2);
});

test("getTrailPoints returns an empty list for missing aircraft", () => {
  assert.deepEqual(getTrailPoints(new Map(), "missing"), []);
  assert.deepEqual(getTrailPoints(new Map(), null), []);
});
