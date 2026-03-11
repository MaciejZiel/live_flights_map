import test from "node:test";
import assert from "node:assert/strict";

import {
  getAircraftRenderMode,
  shouldUseGpuAircraftLayer,
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
      aircraftCount: 320,
      zoom: 4.9,
      clusteringEnabled: false,
    }),
    "lite"
  );
});

test("switches to webgl mode for extreme density", () => {
  assert.equal(
    getAircraftRenderMode({
      aircraftCount: 4000,
      zoom: 4.9,
      clusteringEnabled: false,
    }),
    "webgl"
  );
});

test("keeps detailed markers when traffic is manageable", () => {
  assert.equal(
    getAircraftRenderMode({
      aircraftCount: 120,
      zoom: 7.2,
      clusteringEnabled: false,
    }),
    "detailed"
  );
});

test("enables gpu traffic layer whenever webgl is available and clustering is off", () => {
  assert.equal(
    shouldUseGpuAircraftLayer({
      aircraftCount: 240,
      clusteringEnabled: false,
      webglSupported: true,
    }),
    true
  );
  assert.equal(
    shouldUseGpuAircraftLayer({
      aircraftCount: 240,
      clusteringEnabled: true,
      webglSupported: true,
    }),
    false
  );
  assert.equal(
    shouldUseGpuAircraftLayer({
      aircraftCount: 240,
      clusteringEnabled: false,
      webglSupported: false,
    }),
    false
  );
});

test("preserves detailed markers for selected and watched aircraft in lite mode", () => {
  assert.equal(shouldUseDetailedAircraftMarker("lite", true, false), true);
  assert.equal(shouldUseDetailedAircraftMarker("lite", false, true), true);
  assert.equal(shouldUseDetailedAircraftMarker("lite", false, false), false);
  assert.equal(shouldUseDetailedAircraftMarker("webgl", true, false), true);
  assert.equal(shouldUseDetailedAircraftMarker("webgl", false, true), true);
  assert.equal(shouldUseDetailedAircraftMarker("webgl", false, false), false);
});
