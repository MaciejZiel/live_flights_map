import assert from "node:assert/strict";
import test from "node:test";

import {
  buildGreatCircleLegSegments,
  buildGreatCircleSegments,
} from "../src/lib/utils/geodesic.js";

test("great-circle leg keeps the original endpoints", () => {
  const start = [51.1027, 16.8858];
  const end = [52.1657, 20.9671];
  const segments = buildGreatCircleLegSegments(start, end, { stepKm: 60, maxPoints: 32 });

  assert.equal(segments.length, 1);
  assert.deepEqual(segments[0][0], start);
  assert.deepEqual(segments[0][segments[0].length - 1], end);
});

test("great-circle leg bends away from the flat midpoint for long routes", () => {
  const start = [52.1657, 20.9671];
  const end = [40.6413, -73.7781];
  const segments = buildGreatCircleLegSegments(start, end, { stepKm: 180, maxPoints: 96 });
  const segment = segments[0];
  const midpoint = segment[Math.floor(segment.length / 2)];
  const flatMidLatitude = (start[0] + end[0]) / 2;

  assert.ok(segment.length > 8);
  assert.ok(midpoint[0] > flatMidLatitude);
});

test("multi-leg route builds a continuous set of geodesic segments", () => {
  const route = [
    [51.1027, 16.8858],
    [52.1657, 20.9671],
    [50.0333, 8.5706],
  ];
  const segments = buildGreatCircleSegments(route, { stepKm: 90, maxPoints: 48 });

  assert.ok(segments.length >= 1);
  assert.deepEqual(segments[0][0], route[0]);
  assert.deepEqual(segments[segments.length - 1][segments[segments.length - 1].length - 1], route[2]);
});
