import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAlertEventFingerprint,
  findTransitionAlertMatches,
  getAlertRuleLabel,
  matchesAlertRule,
  normalizeAlertRuleDraft,
} from "../src/lib/utils/alertRules.js";

test("normalizeAlertRuleDraft stores numeric thresholds for altitude and speed", () => {
  assert.deepEqual(normalizeAlertRuleDraft({ type: "altitude_min", query: "12000" }), {
    type: "altitude_min",
    query: "12000",
    payload: {
      threshold: 12000,
    },
    severity: "important",
    cooldownMinutes: 10,
  });

  assert.deepEqual(normalizeAlertRuleDraft({ type: "speed_min", query: "845.5" }), {
    type: "speed_min",
    query: "846",
    payload: {
      threshold: 846,
    },
    severity: "important",
    cooldownMinutes: 10,
  });
});

test("normalizeAlertRuleDraft defaults transition alerts to visible traffic", () => {
  assert.deepEqual(normalizeAlertRuleDraft({ type: "takeoff", query: "" }), {
    type: "takeoff",
    query: "Visible traffic",
    payload: null,
    severity: "critical",
    cooldownMinutes: 10,
  });
});

test("matchesAlertRule handles route, altitude and speed rules", () => {
  const flight = {
    icao24: "48ad08",
    callsign: "LOT285",
    altitude: 12340,
    velocity: 245,
    route_label: "WAW -> JFK",
    airport_codes: "EPWA-KJFK",
    origin: "Warsaw",
    destination: "New York",
  };

  assert.equal(matchesAlertRule(flight, { type: "route", query: "waw-jfk" }), true);
  assert.equal(matchesAlertRule(flight, { type: "altitude_min", query: "12000" }), true);
  assert.equal(matchesAlertRule(flight, { type: "speed_min", query: "900" }), false);
});

test("findTransitionAlertMatches detects takeoff and landing transitions", () => {
  const previousFlightsByIcao24 = new Map([
    ["48ad08", { icao24: "48ad08", on_ground: true }],
    ["3c664f", { icao24: "3c664f", on_ground: false }],
  ]);
  const flights = [
    { icao24: "48ad08", on_ground: false },
    { icao24: "3c664f", on_ground: true },
    { icao24: "4ca123", on_ground: false },
  ];

  assert.deepEqual(
    findTransitionAlertMatches(flights, previousFlightsByIcao24, {
      type: "takeoff",
      query: "Visible traffic",
    }).map((flight) => flight.icao24),
    ["48ad08"]
  );
  assert.deepEqual(
    findTransitionAlertMatches(flights, previousFlightsByIcao24, {
      type: "landing",
      query: "Visible traffic",
    }).map((flight) => flight.icao24),
    ["3c664f"]
  );
});

test("getAlertRuleLabel exposes new rule labels", () => {
  assert.equal(getAlertRuleLabel("altitude_min"), "Altitude");
  assert.equal(getAlertRuleLabel("speed_min"), "Speed");
  assert.equal(getAlertRuleLabel("landing"), "Landing");
});

test("buildAlertEventFingerprint differentiates rule transition and aircraft", () => {
  assert.equal(
    buildAlertEventFingerprint(
      { id: "rule-1", type: "callsign", query: "LOT285" },
      "enter",
      { icao24: "48ad08" }
    ),
    "rule-1:enter:48ad08"
  );
});
