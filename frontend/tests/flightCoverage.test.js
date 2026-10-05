import test from "node:test";
import assert from "node:assert/strict";

import { buildLocalRegionTile } from "../src/lib/utils/flightCoverage.js";

test("local regional supplement stays off at global zoom", () => {
  assert.equal(buildLocalRegionTile({ lamin: -80, lamax: 80, lomin: -170, lomax: 170 }, 2), null);
});

test("zoom changes inside one map cell reuse the same bounded region", () => {
  const firstView = buildLocalRegionTile({ lamin: 51, lamax: 54, lomin: 18, lomax: 21 }, 7);
  const zoomedView = buildLocalRegionTile({ lamin: 51.5, lamax: 53.5, lomin: 18.5, lomax: 20.5 }, 9);

  assert.deepEqual(zoomedView, firstView);
  assert.equal((firstView.bbox.lamax - firstView.bbox.lamin) * (firstView.bbox.lomax - firstView.bbox.lomin), 9);
});

test("panning to a different map cell selects a new regional tile", () => {
  const warsaw = buildLocalRegionTile({ lamin: 51, lamax: 54, lomin: 18, lomax: 21 }, 7);
  const berlin = buildLocalRegionTile({ lamin: 51, lamax: 54, lomin: 12, lomax: 15 }, 7);
  assert.notEqual(warsaw.key, berlin.key);
});
