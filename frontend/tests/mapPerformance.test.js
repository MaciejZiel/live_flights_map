import test from "node:test";
import assert from "node:assert/strict";

import {
  getAircraftRenderMode,
  shouldUseDetailedAircraftMarker,
} from "../src/lib/utils/mapPerformance.js";

test("keeps detailed markers when clustering is enabled", () => {
  assert.equal(
    getAircraftRenderMode({
      aircraftCount: 4200,
      zoom: 4.5,
      clusteringEnabled: true,
    }),
    "detailed"
  );
});

test("switches to lite mode for dense low-zoom traffic", () => {
  assert.equal(
    getAircraftRenderMode({
      aircraftCount: 4000,
      zoom: 4.9,
      clusteringEnabled: false,
    }),
    "lite"
  );
});

test("keeps detailed markers when traffic is manageable", () => {
  assert.equal(
    getAircraftRenderMode({
      aircraftCount: 850,
      zoom: 7.2,
      clusteringEnabled: false,
    }),
    "detailed"
  );
});

test("preserves detailed markers for selected and watched aircraft in lite mode", () => {
  assert.equal(shouldUseDetailedAircraftMarker("lite", true, false), true);
  assert.equal(shouldUseDetailedAircraftMarker("lite", false, true), true);
  assert.equal(shouldUseDetailedAircraftMarker("lite", false, false), false);
});
