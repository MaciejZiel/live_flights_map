import assert from "node:assert/strict";
import test from "node:test";

import { normalizeUserPreferences } from "../src/lib/utils/userPreferences.js";

test("normalizeUserPreferences keeps new frontend filter fields", () => {
  const normalized = normalizeUserPreferences({
    filters: {
      route: "WAW-JFK",
      airportCode: "epwa",
      airportFlow: "departures",
      trafficCategory: "cargo",
    },
    selectedAirportCode: "waw",
    replayWindowMinutes: 180,
    replayPlaybackSpeed: 1.5,
  });

  assert.deepEqual(normalized.filters, {
    query: "",
    minAltitude: "",
    minSpeed: "",
    aircraftType: "",
    country: "",
    operator: "",
    route: "WAW-JFK",
    airportCode: "epwa",
    airportFlow: "departures",
    trafficState: "all",
    trafficCategory: "cargo",
    headingBand: "any",
    hideGroundTraffic: true,
    recentActivity: "any",
    dimFilteredTraffic: true,
  });
  assert.equal(normalized.selectedAirportCode, "WAW");
  assert.equal(normalized.replayWindowMinutes, 180);
  assert.equal(normalized.replayPlaybackSpeed, 1.5);
});

test("normalizeUserPreferences falls back for invalid airport flow and non-object input", () => {
  assert.equal(normalizeUserPreferences(null), null);

  const normalized = normalizeUserPreferences({
    filters: {
      airportFlow: "sideways",
      route: 123,
    },
  });

  assert.equal(normalized.filters.airportFlow, "all");
  assert.equal(normalized.filters.route, "");
});
