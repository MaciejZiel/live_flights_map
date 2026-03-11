import assert from "node:assert/strict";
import test from "node:test";

import { normalizeUserPreferences } from "../src/lib/utils/userPreferences.js";

test("normalizeUserPreferences keeps new frontend filter fields", () => {
  const normalized = normalizeUserPreferences({
    mapStyle: "terrain",
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
    alertDelivery: {
      browserNotificationsEnabled: true,
      browserPermission: "granted",
      webhookEnabled: true,
      webhookUrl: "https://example.com/alerts",
      suppressInfo: true,
    },
  });

  assert.equal(normalized.mapStyle, "terrain");
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
    filters: {
      airportFlow: "sideways",
      route: 123,
    },
  });

  assert.equal(normalized.filters.airportFlow, "all");
  assert.equal(normalized.filters.route, "");
});
