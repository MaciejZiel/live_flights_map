import test from "node:test";
import assert from "node:assert/strict";

import { hasFlightPositionChanged } from "../src/lib/utils/aircraftPosition.js";

test("ignores repeated position snapshots within marker precision", () => {
  assert.equal(hasFlightPositionChanged([52.2297, 21.0122], [52.2297002, 21.0122002]), false);
  assert.equal(hasFlightPositionChanged([52.2297, 21.0122], [52.23, 21.0122]), true);
});

test("treats a missing marker position as an update", () => {
  assert.equal(hasFlightPositionChanged(null, [52.2297, 21.0122]), true);
});
