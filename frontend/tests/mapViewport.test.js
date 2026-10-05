import assert from "node:assert/strict";
import test from "node:test";

import { normalizeMapViewport } from "../src/lib/utils/mapViewport.js";

test("normalizeMapViewport accepts a valid shared map view", () => {
  assert.deepEqual(
    normalizeMapViewport({ center: [52.23, 21.01], zoom: 7.25 }),
    { center: [52.23, 21.01], zoom: 7.25 }
  );
});

test("normalizeMapViewport rejects invalid coordinates and zoom levels", () => {
  assert.equal(normalizeMapViewport({ center: [0, 0], zoom: 0 }), null);
  assert.equal(normalizeMapViewport({ center: [91, 0], zoom: 7 }), null);
  assert.equal(normalizeMapViewport({ center: [52, 181], zoom: 7 }), null);
  assert.equal(normalizeMapViewport({ center: [52, 21], zoom: 19 }), null);
});
