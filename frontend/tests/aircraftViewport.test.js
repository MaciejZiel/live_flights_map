import test from "node:test";
import assert from "node:assert/strict";

import { filterFlightsForMapViewport } from "../src/lib/utils/aircraftViewport.js";

const flights = [
  { icao24: "near", latitude: 52, longitude: 21 },
  { icao24: "far", latitude: 40, longitude: -74 },
  { icao24: "invalid", latitude: null, longitude: 21 },
];

test("filters global traffic to the padded viewport before map rendering", () => {
  const visible = filterFlightsForMapViewport(flights, {
    lamin: 50,
    lamax: 54,
    lomin: 18,
    lomax: 24,
  });

  assert.deepEqual(visible.map((flight) => flight.icao24), ["near"]);
});

test("keeps aircraft visible when a viewport crosses the antimeridian", () => {
  const visible = filterFlightsForMapViewport(
    [
      { icao24: "east", latitude: 0, longitude: 179 },
      { icao24: "west", latitude: 0, longitude: -179 },
      { icao24: "middle", latitude: 0, longitude: 0 },
    ],
    { lamin: -10, lamax: 10, lomin: 170, lomax: 190 }
  );

  assert.deepEqual(visible.map((flight) => flight.icao24), ["east", "west"]);
});
