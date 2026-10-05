import test from "node:test";
import assert from "node:assert/strict";

import {
  formatFlightPositionAge,
  getFlightPositionAgeBand,
  getFlightPositionAgeSeconds,
  getFlightPositionOpacity,
} from "../src/lib/utils/flightFreshness.js";

test("getFlightPositionAgeSeconds accepts epoch seconds and milliseconds", () => {
  const now = 1_800_000_000_000;
  assert.equal(getFlightPositionAgeSeconds({ last_contact: 1_799_999_940 }, now), 60);
  assert.equal(getFlightPositionAgeSeconds({ last_contact: now - 60_000 }, now), 60);
  assert.equal(getFlightPositionAgeSeconds({ last_contact: null }, now), null);
});

test("position age moves through visible freshness bands", () => {
  assert.equal(getFlightPositionAgeBand(10), "fresh");
  assert.equal(getFlightPositionAgeBand(60), "recent");
  assert.equal(getFlightPositionAgeBand(180), "delayed");
  assert.equal(getFlightPositionAgeBand(600), "old");
  assert.equal(getFlightPositionAgeBand(1200), "very-old");
  assert.ok(getFlightPositionOpacity(1200) < getFlightPositionOpacity(10));
});

test("formatFlightPositionAge labels age and preserves unknown timestamps", () => {
  assert.equal(formatFlightPositionAge(42), "seen 42s ago");
  assert.equal(formatFlightPositionAge(125), "seen 2m ago");
  assert.equal(formatFlightPositionAge(7200), "seen 2h ago");
  assert.equal(formatFlightPositionAge(null), "position age unknown");
  assert.equal(formatFlightPositionAge(null, true), "historical position");
});
