import assert from "node:assert/strict";
import test from "node:test";

import { normalizeUserPreferences } from "../src/lib/utils/userPreferences.js";

test("normalizeUserPreferences keeps new frontend filter fields", () => {
  const normalized = normalizeUserPreferences({
    mapStyle: "terrain",
    simpleModeEnabled: false,
    aircraftClusteringEnabled: true,
    filters: {
      route: "WAW-JFK",
      airportCode: "epwa",
      airportFlow: "departures",
      trafficCategory: "cargo",
    },
    workspaceAccountId: "ops-account",
    selectedAirportCode: "waw",
    selectedAirportHistoryHours: 24,
    replayAnchorTimestamp: "2026-03-10T12:00:00Z",
    replayWindowMinutes: 720,
    replayPlaybackSpeed: 1.5,
    recentSearches: ["reg: SP-LVG", "airport: WAW"],
    savedSearches: ["route: WAW-JFK"],
    recentlyViewedFlights: [
      {
        icao24: "48af19",
        callsign: "LOT285",
        registration: "SP-LVQ",
        altitude: 11020,
      },
    ],
    alertDelivery: {
      browserNotificationsEnabled: true,
      browserPermission: "granted",
      webhookEnabled: true,
      webhookUrl: "https://example.com/alerts",
      suppressInfo: true,
    },
  });

  assert.equal(normalized.mapStyle, "terrain");
  assert.equal(normalized.simpleModeEnabled, false);
  assert.equal(normalized.aircraftClusteringEnabled, true);
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
  assert.equal(normalized.workspaceAccountId, "ops-account");
  assert.equal(normalized.selectedAirportCode, "WAW");
  assert.equal(normalized.selectedAirportHistoryHours, 24);
  assert.equal(normalized.replayAnchorTimestamp, "2026-03-10T12:00:00.000Z");
  assert.equal(normalized.replayWindowMinutes, 720);
  assert.equal(normalized.replayPlaybackSpeed, 1.5);
  assert.deepEqual(normalized.recentSearches, ["reg: SP-LVG", "airport: WAW"]);
  assert.deepEqual(normalized.savedSearches, ["route: WAW-JFK"]);
  assert.deepEqual(normalized.recentlyViewedFlights, [
    {
      icao24: "48af19",
      callsign: "LOT285",
      registration: "SP-LVQ",
      type_code: "",
      route_label: "",
      origin_country: "",
      altitude: 11020,
      velocity: null,
      last_contact: null,
      latitude: null,
      longitude: null,
    },
  ]);
  assert.deepEqual(normalized.alertDelivery, {
    browserNotificationsEnabled: true,
    browserPermission: "granted",
    webhookEnabled: true,
    webhookUrl: "https://example.com/alerts",
    suppressInfo: true,
  });
});

test("normalizeUserPreferences falls back for invalid airport flow and non-object input", () => {
  assert.equal(normalizeUserPreferences(null), null);

  const normalized = normalizeUserPreferences({
    simpleModeEnabled: "nope",
    recentSearches: ["airport: WAW", 123, "route: EHAM-KJFK"],
    savedSearches: ["reg: SP-LVG", null],
    recentlyViewedFlights: [{ icao24: "ABC123" }, { foo: "bar" }],
    filters: {
      airportFlow: "sideways",
      route: 123,
    },
  });

  assert.equal(normalized.simpleModeEnabled, true);
  assert.deepEqual(normalized.recentSearches, ["airport: WAW", "route: EHAM-KJFK"]);
  assert.deepEqual(normalized.savedSearches, ["reg: SP-LVG"]);
  assert.deepEqual(normalized.recentlyViewedFlights, [
    {
      icao24: "abc123",
      callsign: "",
      registration: "",
      type_code: "",
      route_label: "",
      origin_country: "",
      altitude: null,
      velocity: null,
      last_contact: null,
      latitude: null,
      longitude: null,
    },
  ]);
  assert.equal(normalized.filters.airportFlow, "all");
  assert.equal(normalized.filters.route, "");
});
