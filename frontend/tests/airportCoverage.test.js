import test from "node:test";
import assert from "node:assert/strict";

import { buildAirportCoverageRequest } from "../src/lib/utils/airportCoverage.js";

test("reuses an airport cache cell when zooming within one coverage tier", () => {
  const firstView = buildAirportCoverageRequest(
    { lamin: 51, lamax: 54, lomin: 18, lomax: 21 },
    7.2
  );
  const zoomedView = buildAirportCoverageRequest(
    { lamin: 51.5, lamax: 53.5, lomin: 18.5, lomax: 20.5 },
    7.8
  );

  assert.equal(firstView.key, zoomedView.key);
  assert.deepEqual(firstView.bbox, zoomedView.bbox);
});

test("uses smaller airport cells and more detail at higher zoom", () => {
  const regional = buildAirportCoverageRequest(
    { lamin: 51, lamax: 54, lomin: 18, lomax: 21 },
    7
  );
  const detailed = buildAirportCoverageRequest(
    { lamin: 51, lamax: 54, lomin: 18, lomax: 21 },
    10
  );

  assert.notEqual(regional.key, detailed.key);
  assert.ok(detailed.limit > regional.limit);
  assert.ok(detailed.bbox.lamax - detailed.bbox.lamin < regional.bbox.lamax - regional.bbox.lamin);
});

test("keeps coverage bounds inside the valid world extent", () => {
  const request = buildAirportCoverageRequest(
    { lamin: 85, lamax: 90, lomin: 179, lomax: 180 },
    10
  );

  assert.ok(request.bbox.lamax <= 90);
  assert.equal(request.bbox.lomax, 180);
});
