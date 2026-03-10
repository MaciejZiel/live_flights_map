import assert from "node:assert/strict";
import test from "node:test";

import { classifyTrafficCategory } from "../src/lib/utils/trafficCategories.js";

test("classifyTrafficCategory recognizes explicit cargo operators", () => {
  assert.equal(
    classifyTrafficCategory({
      operator_code: "FDX",
      type_code: "B763",
    }),
    "cargo"
  );
});

test("classifyTrafficCategory recognizes helicopters and light aircraft", () => {
  assert.equal(
    classifyTrafficCategory({
      type_code: "EC35",
    }),
    "helicopter"
  );

  assert.equal(
    classifyTrafficCategory({
      type_code: "P28A",
      velocity: 55,
      altitude: 1200,
    }),
    "light"
  );
});

test("classifyTrafficCategory falls back to passenger jets", () => {
  assert.equal(
    classifyTrafficCategory({
      callsign: "LOT285",
      type_code: "B38M",
      velocity: 220,
      altitude: 10000,
    }),
    "passenger"
  );
});
