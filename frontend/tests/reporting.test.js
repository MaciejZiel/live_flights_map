import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAirportReportCsv,
  buildPrintableRadarReport,
  buildTrafficReportCsv,
} from "../src/lib/utils/reporting.js";

test("buildTrafficReportCsv exports enriched route fields", () => {
  const csv = buildTrafficReportCsv([
    {
      callsign: "LOT285",
      icao24: "abc123",
      registration: "SP-LVQ",
      operator_code: "LOT",
      route_label: "WAW-JFK",
      origin: "WAW",
      destination: "JFK",
      altitude: 10668,
      velocity: 230,
      on_ground: false,
    },
  ]);

  assert.match(csv, /callsign,icao24,registration/);
  assert.match(csv, /LOT285,abc123,SP-LVQ/);
  assert.match(csv, /WAW-JFK/);
  assert.match(csv, /828/);
});

test("buildAirportReportCsv includes arrivals, departures and nearby rows", () => {
  const csv = buildAirportReportCsv(
    { iata: "WAW" },
    {
      recent: {
        arrivals: [{ callsign: "LOT1", origin: "JFK", destination: "WAW" }],
        departures: [{ callsign: "LOT2", origin: "WAW", destination: "LHR" }],
      },
      live: {
        nearby: [{ callsign: "LOT3", on_ground: true }],
      },
    }
  );

  assert.match(csv, /arrival,LOT1/);
  assert.match(csv, /departure,LOT2/);
  assert.match(csv, /ground,LOT3/);
});

test("buildPrintableRadarReport renders a printable HTML report", () => {
  const html = buildPrintableRadarReport({
    title: "Radar report",
    generatedAt: "2026-03-10 12:00 UTC",
    summaryRows: [{ label: "Visible traffic", value: "42" }],
    flights: [{ callsign: "LOT285", route_label: "WAW-JFK", on_ground: false }],
  });

  assert.match(html, /Radar report/);
  assert.match(html, /Visible traffic/);
  assert.match(html, /LOT285/);
  assert.match(html, /WAW-JFK/);
  assert.match(html, /Generated 2026-03-10 12:00 UTC/);
});
